import os
import uuid
# Глобальные импорты Flask (БЕЗ current_user!)
from flask import Blueprint, render_template, redirect, request, jsonify, abort, Response, session
# Импорты для работы с сессиями авторизованных пользователей
from flask_login import login_required, current_user

# Подключение кодовой базы данных Luma
from data import db_session
from data.users import LumaMediaAccount, User
from data.video import Video, Clip
from forms.video import VideoUploadForm, ClipUploadForm, CreateMediaAccountForm

# Безопасный импорт утилит для предотвращения циклических зависимостей
from utils import compress_video_thumbnail, UPLOAD_FOLDER

media_bp = Blueprint('media', __name__)

@media_bp.route('/media/create', methods=['GET', 'POST'])
@login_required
def create_media_account():
    form = CreateMediaAccountForm()
    db_sess = db_session.create_session()
    try:
        existing_count = db_sess.query(LumaMediaAccount).filter_by(luma_user_id=current_user.id).count()
        if existing_count >= 5:
            return render_template('create_media.html', title='Лимит достигнут', form=form,
                                   message='Нельзя привязать более 5 аккаунтов Luma Media к одному профилю Luma.')

        if form.validate_on_submit():
            if db_sess.query(LumaMediaAccount).filter_by(channel_name=form.channel_name.data).first():
                return render_template('create_media.html', title='Ошибка', form=form,
                                       message='Такое название канала уже занято.')

            new_media = LumaMediaAccount(
                channel_name=form.channel_name.data,
                luma_user_id=current_user.id
            )
            db_sess.add(new_media)
            db_sess.commit()
            return redirect(f'/profile/{current_user.nickname}')
    finally:
        db_sess.close()

    return render_template('create_media.html', title='Создать медиа-профиль', form=form)


# ИСПРАВЛЕНИЕ МАРШРУТА v0.98.4.6: Перевод на единую ссылку /media
@media_bp.route('/media')
def video_index():
    """Единый медиаэкран Luma Media: шахматное переплетение Video и Ленты Клипов (v0.98.4.6)"""
    db_sess = db_session.create_session()
    try:
        feed_type = request.args.get('feed', 'all')

        # Получаем массив клипов для горизонтальной карусели Shorts
        all_clips = db_sess.query(Clip).order_by(Clip.created_date.desc()).limit(15).all()

        if feed_type == 'subs' and current_user.is_authenticated:
            subscriptions = db_sess.query(ChannelSubscription).filter_by(user_id=current_user.id).all()
            subscribed_channel_ids = [sub.media_account_id for sub in subscriptions]

            if subscribed_channel_ids:
                videos = db_sess.query(Video).filter(Video.media_account_id.in_(subscribed_channel_ids)).order_by(
                    Video.created_date.desc()).all()
            else:
                videos = []
        else:
            videos = db_sess.query(Video).order_by(Video.created_date.desc()).all()
            feed_type = 'all'

        return render_template('video_index.html', title='Luma Media', videos=videos, clips=all_clips,
                               feed_type=feed_type)
    finally:
        db_sess.close()


@media_bp.route('/videos/upload', methods=['GET', 'POST'])
@login_required
def video_upload():
    form = VideoUploadForm()
    db_sess = db_session.create_session()
    try:
        user_channels = db_sess.query(LumaMediaAccount).filter_by(luma_user_id=current_user.id).all()
        if not user_channels:
            form.channel_id.choices = [(-1, "-- Сначала создайте канал в профиле --")]
            return render_template('video_upload.html', title='Загрузка видео', form=form,
                                   message='У вас нет созданных каналов Luma Media. Перейдите в свой Профиль, чтобы создать его.')
        else:
            form.channel_id.choices = [(c.id, c.channel_name) for c in user_channels]

        if form.validate_on_submit():
            if form.channel_id.data == -1:
                return render_template('video_upload.html', title='Загрузка видео', form=form,
                                       message='Вы не можете опубликовать видео без активного канала.')

            selected_channel = db_sess.get(LumaMediaAccount, form.channel_id.data)
            if not selected_channel or selected_channel.luma_user_id != current_user.id:
                abort(403)

            video_file = form.video.data
            thumb_file = form.thumbnail.data
            if not video_file:
                return render_template('video_upload.html', title='Загрузка видео', form=form, message='Файл видео обязателен')

            ext = video_file.filename.split('.')[-1].lower()
            video_filename = f"{uuid.uuid4().hex}.{ext}"
            video_rel_path = f"videos/{video_filename}"
            video_full_path = os.path.join(UPLOAD_FOLDER, video_rel_path)
            video_file.save(video_full_path)

            from utils import generate_video_first_frame

            thumb_path = None
            if thumb_file and thumb_file.filename and not thumb_file.filename.startswith('._'):
                thumb_path = compress_video_thumbnail(thumb_file)
            else:
                thumb_path = generate_video_first_frame(video_full_path)

            new_video = Video(
                title=form.title.data,
                description=form.description.data,
                video_path=f"/static/{video_rel_path}",
                thumbnail_path=thumb_path,
                media_account_id=form.channel_id.data
            )
            db_sess.add(new_video)
            db_sess.commit()
            return redirect('/media')
    finally:
        db_sess.close()

    return render_template('video_upload.html', title='Загрузка видео', form=form)



from data.video import ChannelSubscription, VideoLike, VideoDislike, LumaRepost


@media_bp.route('/videos/<int:video_id>')
def video_watch(video_id):
    """Страница просмотра конкретного видеоролика с поддержкой кастомного плеера Luma (v0.98.4.2)"""
    db_sess = db_session.create_session()
    try:
        video = db_sess.get(Video, video_id)
        if not video:
            abort(404)

        video.views += 1
        db_sess.commit()

        # Извлекаем медиа-канал
        channel = db_sess.get(LumaMediaAccount, video.media_account_id)

        # Подсчет подписчиков и флагов подписки/реакций
        subs_count = db_sess.query(ChannelSubscription).filter_by(media_account_id=channel.id).count()

        # --- ФИКС v0.98.4.2: Считаем общее количество репостов видео на бэкенде ---
        total_video_reps = db_sess.query(LumaRepost).filter_by(content_type='video', content_id=video.id).count()

        is_subbed = False
        is_liked = False
        is_disliked = False

        if current_user.is_authenticated:
            is_subbed = db_sess.query(ChannelSubscription).filter_by(
                user_id=current_user.id,
                media_account_id=channel.id
            ).first() is not None

            is_liked = db_sess.query(VideoLike).filter_by(
                user_id=current_user.id,
                video_id=video.id
            ).first() is not None

            is_disliked = db_sess.query(VideoDislike).filter_by(
                user_id=current_user.id,
                video_id=video.id
            ).first() is not None

        recommended = db_sess.query(Video).filter(Video.id != video_id).limit(6).all()

        return render_template(
            'video_watch.html',
            title=video.title,
            video=video,
            recommended=recommended,
            channel=channel,
            subs_count=subs_count,
            is_subbed=is_subbed,
            is_liked=is_liked,
            is_disliked=is_disliked,
            total_video_reps=total_video_reps  # Передаем готовое число в разметку
        )
    finally:
        db_sess.close()


@media_bp.route('/videos/stream/<int:video_id>')
def video_stream(video_id):
    db_sess = db_session.create_session()
    try:
        video = db_sess.get(Video, video_id)
        if not video:
            abort(404)

        file_path = video.video_path.lstrip('/')
        if not os.path.exists(file_path):
            abort(404)

        file_size = os.path.getsize(file_path)
        range_header = request.headers.get('Range', None)
        byte_start = 0
        byte_end = file_size - 1

        if range_header:
            range_value = range_header.strip().split('=')[-1]
            range_parts = range_value.split('-')
            if range_parts[0]:
                byte_start = int(range_parts[0])
            if len(range_parts) > 1 and range_parts[1]:
                byte_end = int(range_parts[1])

        chunk_size = min(1024 * 1024, byte_end - byte_start + 1)
        byte_end = byte_start + chunk_size - 1

        def generate_video_chunks():
            with open(file_path, 'rb') as f:
                f.seek(byte_start)
                remaining = chunk_size
                while remaining > 0:
                    read_size = min(4096, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    yield data
                    remaining -= len(data)

        response = Response(generate_video_chunks(), status=206, mimetype='video/mp4', direct_passthrough=True)
        response.headers.add('Content-Range', f'bytes {byte_start}-{byte_end}/{file_size}')
        response.headers.add('Accept-Ranges', 'bytes')
        response.headers.add('Content-Length', str(chunk_size))
        return response
    finally:
        db_sess.close()


@media_bp.route('/api/videos/<int:video_id>/like', methods=['POST'])
@login_required
def toggle_like(video_id):
    from data.video import VideoLike, VideoDislike
    db_sess = db_session.create_session()
    try:
        video = db_sess.get(Video, video_id)
        if not video:
            return jsonify({'error': 'Видео не найдено'}), 404

        existing_like = db_sess.query(VideoLike).filter_by(user_id=current_user.id, video_id=video_id).first()
        existing_dislike = db_sess.query(VideoDislike).filter_by(user_id=current_user.id, video_id=video_id).first()

        if existing_like:
            db_sess.delete(existing_like)
            user_has_liked = False
        else:
            new_like = VideoLike(user_id=current_user.id, video_id=video_id)
            db_sess.add(new_like)
            user_has_liked = True
            if existing_dislike:
                db_sess.delete(existing_dislike)

        db_sess.commit()
        return jsonify({'score': video.get_rating_score(), 'liked': user_has_liked, 'disliked': False})
    finally:
        db_sess.close()


@media_bp.route('/api/videos/<int:video_id>/dislike', methods=['POST'])
@login_required
def toggle_dislike(video_id):
    from data.video import VideoLike, VideoDislike
    db_sess = db_session.create_session()
    try:
        video = db_sess.get(Video, video_id)
        if not video:
            return jsonify({'error': 'Видео не найдено'}), 404

        existing_like = db_sess.query(VideoLike).filter_by(user_id=current_user.id, video_id=video_id).first()
        existing_dislike = db_sess.query(VideoDislike).filter_by(user_id=current_user.id, video_id=video_id).first()

        if existing_dislike:
            db_sess.delete(existing_dislike)
            user_has_disliked = False
        else:
            new_dislike = VideoDislike(user_id=current_user.id, video_id=video_id)
            db_sess.add(new_dislike)
            user_has_disliked = True
            if existing_like:
                db_sess.delete(existing_like)

        db_sess.commit()
        return jsonify({'score': video.get_rating_score(), 'liked': False, 'disliked': user_has_disliked})
    finally:
        db_sess.close()


@media_bp.route('/api/videos/<int:video_id>/comments', methods=['GET'])
def get_video_comments(video_id):
    db_sess = db_session.create_session()
    try:
        video = db_sess.get(Video, video_id)
        if not video:
            return jsonify({'error': 'Видео не найдено'}), 404
        comments_data = [{
            'id': comment.id,
            'nickname': comment.user.nickname,
            'text': comment.text,
            'date': comment.created_date.strftime('%d.%m.%Y %H:%M')
        } for comment in video.comments]
        return jsonify({'comments': comments_data})
    finally:
        db_sess.close()

@media_bp.route('/api/videos/<int:video_id>/comments', methods=['POST'])
@login_required
def add_video_comment(video_id):
    from data.video import VideoComment
    data = request.get_json() or {}
    comment_text = data.get('text', '').strip()
    if not comment_text:
        return jsonify({'error': 'Текст комментария пуст'}), 400

    db_sess = db_session.create_session()
    try:
        video = db_sess.get(Video, video_id)
        if not video:
            return jsonify({'error': 'Видео не найдено'}), 404

        new_comment = VideoComment(video_id=video_id, user_id=current_user.id, text=comment_text)
        db_sess.add(new_comment)
        db_sess.commit()
        return jsonify({
            'success': True,
            'comment': {
                'id': new_comment.id,
                'nickname': current_user.nickname,
                'text': comment_text,
                'date': new_comment.created_date.strftime('%d.%m.%Y %H:%M')
            }
        })
    finally:
        db_sess.close()


from data.video import Clip, LumaRepost  # Проверьте корректность импортов


@media_bp.route('/clips')
def clips_index():
    """Страница бесконечной ленты Shorts с умным фокусом на выбранный clip_id (v0.98.4.4)"""
    db_sess = db_session.create_session()
    try:
        target_clip_id = request.args.get('clip_id', type=int)

        # Получаем базовый массив клипов
        all_clips = db_sess.query(Clip).order_by(Clip.created_date.desc()).all()

        # Если передан конкретный ID, перестраиваем массив, чтобы он шел первым
        if target_clip_id:
            target_clip = db_sess.get(Clip, target_clip_id)
            if target_clip:
                # Фильтруем массив, убирая дубликат, и ставим целевой клип в начало
                filtered_clips = [c for c in all_clips if c.id != target_clip_id]
                clips = [target_clip] + filtered_clips
            else:
                clips = all_clips
        else:
            clips = all_clips

        for clip in clips:
            clip.total_reposts = db_sess.query(LumaRepost).filter_by(content_type='clip', content_id=clip.id).count()

        return render_template('clips_index.html', title='Клипы Luma', clips=clips)
    finally:
        db_sess.close()


@media_bp.route('/clips/upload', methods=['GET', 'POST'])
@login_required
def clip_upload():
    form = ClipUploadForm()
    db_sess = db_session.create_session()
    try:
        user_channels = db_sess.query(LumaMediaAccount).filter_by(luma_user_id=current_user.id).all()
        if not user_channels:
            form.channel_id.choices = [(-1, "-- Сначала создайте канал в профиле --")]
            return render_template('clip_upload.html', title='Загрузить клип', form=form,
                                   message='У вас нет созданных навсегда каналов Luma Media. Перейдите в свой Профиль, чтобы создать его.')
        else:
            form.channel_id.choices = [(c.id, c.channel_name) for c in user_channels]

        if form.validate_on_submit():
            if form.channel_id.data == -1:
                return render_template('clip_upload.html', title='Загрузить клип', form=form, message='Вы не можете опубликовать клип без активного канала.')

            selected_channel = db_sess.get(LumaMediaAccount, form.channel_id.data)
            if not selected_channel or selected_channel.luma_user_id != current_user.id:
                abort(403)

            video_file = form.video.data
            thumb_file = form.thumbnail.data
            if not video_file:
                return render_template('clip_upload.html', title='Загрузить клип', form=form, message='Файл видео обязателен')

            thumb_path = '/static/thumbnails/default_video.png'
            if thumb_file:
                thumb_path = compress_video_thumbnail(thumb_file)

            ext = video_file.filename.split('.')[-1].lower()
            video_filename = f"clip_{uuid.uuid4().hex}.{ext}"
            video_rel_path = f"videos/{video_filename}"
            video_full_path = os.path.join(UPLOAD_FOLDER, video_rel_path)
            video_file.save(video_full_path)

            new_clip = Clip(title=form.title.data, video_path=f"/static/{video_rel_path}", thumbnail_path=thumb_path, media_account_id=form.channel_id.data)
            db_sess.add(new_clip)
            db_sess.commit()
            return redirect('/media')
    finally:
        db_sess.close()
    return render_template('clip_upload.html', title='Загрузить клип', form=form)


@media_bp.route('/clips/stream/<int:clip_id>')
def clip_stream(clip_id):
    db_sess = db_session.create_session()
    try:
        clip = db_sess.get(Clip, clip_id)
        if not clip:
            abort(404)

        file_path = clip.video_path.lstrip('/')
        if not os.path.exists(file_path):
            abort(404)

        file_size = os.path.getsize(file_path)
        range_header = request.headers.get('Range', None)
        byte_start = 0
        byte_end = file_size - 1

        if range_header:
            range_value = range_header.strip().split('=')[-1]
            range_parts = range_value.split('-')
            if range_parts and range_parts[0]:
                byte_start = int(range_parts[0])
            if len(range_parts) > 1 and range_parts[1]:
                byte_end = int(range_parts[1])

        chunk_size = min(1024 * 1024, byte_end - byte_start + 1)
        byte_end = byte_start + chunk_size - 1

        def generate_clip_chunks():
            with open(file_path, 'rb') as f:
                f.seek(byte_start)
                remaining = chunk_size
                while remaining > 0:
                    read_size = min(4096, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    yield data
                    remaining -= len(data)

        response = Response(generate_clip_chunks(), status=206, mimetype='video/mp4', direct_passthrough=True)
        response.headers.add('Content-Range', f'bytes {byte_start}-{byte_end}/{file_size}')
        response.headers.add('Accept-Ranges', 'bytes')
        response.headers.add('Content-Length', str(chunk_size))
        return response
    finally:
        db_sess.close()


@media_bp.route('/api/clips/<int:clip_id>/like', methods=['POST'])
@login_required
def like_clip(clip_id):
    db_sess = db_session.create_session()
    try:
        clip = db_sess.get(Clip, clip_id)
        if not clip:
            return jsonify({'error': 'Клип не найден'}), 404

        session_key = f"clip_liked_{clip_id}"
        if session.get(session_key):
            clip.likes_count = max(0, clip.likes_count - 1)
            session.pop(session_key, None)
            status_liked = False
        else:
            clip.likes_count += 1
            session[session_key] = True
            status_liked = True

        db_sess.commit()
        return jsonify({'likes': clip.likes_count, 'liked': status_liked})
    finally:
        db_sess.close()


from forms.video import EditMediaChannelForm  # Укажите ваш корректный файл импорта формы
from utils import compress_and_save_image, compress_channel_banner, compress_player_icon


@media_bp.route('/media/edit/<int:channel_id>', methods=['GET', 'POST'])
@login_required
def edit_media_account(channel_id):
    """Страница настройки и кастомизации внешнего вида канала Luma Media."""
    db_sess = db_session.create_session()
    try:
        channel = db_sess.get(LumaMediaAccount, channel_id)
        if not channel:
            abort(404)

        # Защита: редактировать канал может только его непосредственный создатель
        if channel.luma_user_id != current_user.id:
            abort(403)

        form = EditMediaChannelForm()

        if form.validate_on_submit():
            # Проверка уникальности имени, если оно изменилось
            if form.channel_name.data != channel.channel_name:
                clashing = db_sess.query(LumaMediaAccount).filter_by(channel_name=form.channel_name.data).first()
                if clashing:
                    return render_template('edit_channel.html', title='Настройка канала', form=form, channel=channel,
                                           message='Это название канала уже занято.')
                channel.channel_name = form.channel_name.data

            channel.description = form.description.data

            # Обработка загрузки аватара канала
            if form.avatar.data and form.avatar.data.filename:
                channel.avatar_path = compress_and_save_image(form.avatar.data)

            # Обработка загрузки баннера канала
            if form.banner.data and form.banner.data.filename:
                channel.banner_path = compress_channel_banner(form.banner.data)

            # Обработка загрузки вотермарки для видеоплеера (для версии 0.98.3.6)
            if form.player_icon.data and form.player_icon.data.filename:
                channel.player_icon_path = compress_player_icon(form.player_icon.data)

            db_sess.commit()
            return redirect(f'/profile/{current_user.nickname}')

        elif request.method == 'GET':
            # Предзаполнение формы текущими данными
            form.channel_name.data = channel.channel_name
            form.description.data = channel.description

        return render_template('edit_channel.html', title='Настройка канала', form=form, channel=channel)
    finally:
        db_sess.close()

@media_bp.route('/studio')
@login_required
def luma_studio():
    """Панель Творческой студии Luma (Luma Studio) для авторов (v0.98.3.4)"""
    db_sess = db_session.create_session()
    try:
        # Получаем все каналы текущего пользователя
        my_channels = db_sess.query(LumaMediaAccount).filter_by(luma_user_id=current_user.id).all()
        channel_ids = [c.id for c in my_channels]

        # Инициализируем метрики аналитики
        total_views = 0
        total_videos_count = 0
        total_clips_count = 0
        all_videos = []
        all_clips = []

        if channel_ids:
            # Сбор видеороликов и подсчет просмотров
            all_videos = db_sess.query(Video).filter(Video.media_account_id.in_(channel_ids)).order_by(Video.created_date.desc()).all()
            total_videos_count = len(all_videos)
            total_views = sum(v.views for v in all_videos)

            # Сбор клипов
            all_clips = db_sess.query(Clip).filter(Clip.media_account_id.in_(channel_ids)).order_by(Clip.created_date.desc()).all()
            total_clips_count = len(all_clips)

        return render_template(
            'studio.html',
            title='Творческая студия Luma',
            channels=my_channels,
            videos=all_videos,
            clips=all_clips,
            total_views=total_views,
            total_videos=total_videos_count,
            total_clips=total_clips_count
        )
    finally:
        db_sess.close()


@media_bp.route('/studio/video/delete/<int:video_id>', methods=['POST'])
@login_required
def delete_video(video_id):
    """Безопасное удаление видео через Творческую студию"""
    db_sess = db_session.create_session()
    try:
        video = db_sess.get(Video, video_id)
        if not video:
            abort(404)

        # Проверка прав: видео принадлежит одному из каналов пользователя
        channel = db_sess.get(LumaMediaAccount, video.media_account_id)
        if not channel or channel.luma_user_id != current_user.id:
            abort(403)

        # Физическое удаление файлов с диска сервера (видео + обложка)
        if video.video_path and os.path.exists(video.video_path.lstrip('/')):
            os.remove(video.video_path.lstrip('/'))
        if video.thumbnail_path and "default_video.png" not in video.thumbnail_path:
            if os.path.exists(video.thumbnail_path.lstrip('/')):
                os.remove(video.thumbnail_path.lstrip('/'))

        db_sess.delete(video)
        db_sess.commit()
        return redirect('/studio')
    finally:
        db_sess.close()


@media_bp.route('/studio/clip/delete/<int:clip_id>', methods=['POST'])
@login_required
def delete_clip(clip_id):
    """Безопасное удаление клипа через Творческую студию"""
    db_sess = db_session.create_session()
    try:
        clip = db_sess.get(Clip, clip_id)
        if not clip:
            abort(404)

        channel = db_sess.get(LumaMediaAccount, clip.media_account_id)
        if not channel or channel.luma_user_id != current_user.id:
            abort(403)

        if clip.video_path and os.path.exists(clip.video_path.lstrip('/')):
            os.remove(clip.video_path.lstrip('/'))
        if clip.thumbnail_path and "default_video.png" not in clip.thumbnail_path:
            if os.path.exists(clip.thumbnail_path.lstrip('/')):
                os.remove(clip.thumbnail_path.lstrip('/'))

        db_sess.delete(clip)
        db_sess.commit()
        return redirect('/studio')
    finally:
        db_sess.close()


from data.video import ChannelSubscription  # Укажите ваш правильный путь импорта


@media_bp.route('/api/channel/<int:channel_id>/subscribe', methods=['POST'])
@login_required
def toggle_subscribe(channel_id):
    """Асинхронный экшен подписки/отписки от канала Luma Media без Redis"""
    db_sess = db_session.create_session()
    try:
        channel = db_sess.get(LumaMediaAccount, channel_id)
        if not channel:
            return jsonify({'error': 'Канал не найден'}), 404

        if channel.luma_user_id == current_user.id:
            return jsonify({'error': 'Нельзя подписаться на собственный канал'}), 400

        # Проверяем, существует ли уже подписка
        existing_sub = db_sess.query(ChannelSubscription).filter_by(
            user_id=current_user.id,
            media_account_id=channel_id
        ).first()

        if existing_sub:
            db_sess.delete(existing_sub)
            subscribed = False
        else:
            new_sub = ChannelSubscription(user_id=current_user.id, media_account_id=channel_id)
            db_sess.add(new_sub)
            subscribed = True

        db_sess.commit()

        # Считаем актуальное количество подписчиков
        subs_count = db_sess.query(ChannelSubscription).filter_by(media_account_id=channel_id).count()

        return jsonify({
            'subscribed': subscribed,
            'subs_count': subs_count
        })
    finally:
        db_sess.close()

from data.video import LumaRepost # Проверьте корректность вашего импорта

@media_bp.route('/api/repost/my-channels', methods=['GET'])
@login_required
def get_channels_for_repost():
    """Возвращает JSON со списком каналов текущего пользователя для модального окна репоста"""
    db_sess = db_session.create_session()
    try:
        channels = db_sess.query(LumaMediaAccount).filter_by(luma_user_id=current_user.id).all()
        return jsonify({
            'channels': [{'id': c.id, 'name': c.channel_name} for c in channels]
        })
    finally:
        db_sess.close()


@media_bp.route('/api/repost/add', methods=['POST'])
@login_required
def add_content_repost():
    """Асинхронный эндпоинт публикации репоста на выбранный канал Luma Media"""
    data = request.get_json() or {}
    target_channel_id = data.get('channel_id')
    content_type = data.get('content_type') # 'video' или 'clip'
    content_id = data.get('content_id')

    if not target_channel_id or content_type not in ['video', 'clip'] or not content_id:
        return jsonify({'error': 'Неверные параметры запроса'}), 400

    db_sess = db_session.create_session()
    try:
        # Проверка прав: канал действительно принадлежит текущему пользователю
        channel = db_sess.get(LumaMediaAccount, target_channel_id)
        if not channel or channel.luma_user_id != current_user.id:
            return jsonify({'error': 'Доступ запрещен'}), 403

        # Проверяем существование репоста
        existing = db_sess.query(LumaRepost).filter_by(
            media_account_id=target_channel_id,
            content_type=content_type,
            content_id=content_id
        ).first()

        if existing:
            return jsonify({'error': 'Вы уже зарепостили этот контент на данный канал!'}), 400

        # Создаем запись репоста
        new_repost = LumaRepost(
            media_account_id=target_channel_id,
            content_type=content_type,
            content_id=int(content_id)
        )
        db_sess.add(new_repost)
        db_sess.commit()

        # Считаем общее количество реpostов этого объекта во всей системе
        total_reposts = db_sess.query(LumaRepost).filter_by(content_type=content_type, content_id=content_id).count()

        return jsonify({
            'success': True,
            'total_reposts': total_reposts
        })
    finally:
        db_sess.close()


@media_bp.route('/channel/<int:channel_id>')
def channel_view(channel_id):
    """Публичная страница канала Luma Media с вкладкой Репосты (v0.98.4.2)"""
    db_sess = db_session.create_session()
    try:
        channel = db_sess.get(LumaMediaAccount, channel_id)
        if not channel:
            abort(404)

        channel_videos = db_sess.query(Video).filter_by(media_account_id=channel_id).order_by(
            Video.created_date.desc()).all()
        channel_clips = db_sess.query(Clip).filter_by(media_account_id=channel_id).order_by(
            Clip.created_date.desc()).all()

        # ИЗВЛЕЧЕНИЕ РЕПОСТОВ КАНАЛА v0.98.4.2
        reposts_raw = db_sess.query(LumaRepost).filter_by(media_account_id=channel_id).order_by(
            LumaRepost.created_date.desc()).all()

        # Обновленный цикл сборки репостов v0.98.4.3
        reposted_content = []
        for rep in reposts_raw:
            if rep.content_type == 'video':
                item = db_sess.get(Video, rep.content_id)
                if item:
                    reposted_content.append({
                        'repost_id': rep.id,  # Передаем ID для экшена удаления
                        'type': 'video',
                        'data': item,
                        'repost_date': rep.created_date
                    })
            elif rep.content_type == 'clip':
                item = db_sess.get(Clip, rep.content_id)
                if item:
                    reposted_content.append({
                        'repost_id': rep.id,  # Передаем ID для экшена удаления
                        'type': 'clip',
                        'data': item,
                        'repost_date': rep.created_date
                    })

        owner = db_sess.get(User, channel.luma_user_id)
        subs_count = db_sess.query(ChannelSubscription).filter_by(media_account_id=channel_id).count()

        is_subbed = False
        if current_user.is_authenticated:
            is_subbed = db_sess.query(ChannelSubscription).filter_by(user_id=current_user.id,
                                                                     media_account_id=channel_id).first() is not None

        return render_template(
            'channel.html',
            title=f'Канал {channel.channel_name}',
            channel=channel,
            videos=channel_videos,
            clips=channel_clips,
            reposts=reposted_content,  # Передаем репосты в шаблон
            owner=owner,
            subs_count=subs_count,
            is_subbed=is_subbed
        )
    finally:
        db_sess.close()


import cv2  # Убедитесь, что opencv-python установлен в виртуальном окружении
from data.video import LumaRepost


@media_bp.route('/repost/delete/<int:repost_id>', methods=['POST'])
@login_required
def delete_repost(repost_id):
    """Экшен удаления репоста с канала Luma Media автором (v0.98.4.3)"""
    db_sess = db_session.create_session()
    try:
        repost = db_sess.get(LumaRepost, repost_id)
        if not repost:
            abort(404)

        # Защита: удалить репост может только владелец канала
        channel = db_sess.get(LumaMediaAccount, repost.media_account_id)
        if not channel or channel.luma_user_id != current_user.id:
            abort(403)

        db_sess.delete(repost)
        db_sess.commit()
        return redirect(f'/channel/{channel.id}')
    finally:
        db_sess.close()
