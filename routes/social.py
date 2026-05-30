from flask import Blueprint, render_template, redirect, url_for, abort, flash
from flask_login import login_required, current_user
from data import db_session
from data.users import User, followers

social_bp = Blueprint('social', __name__)


@social_bp.route('/follow/<string:nickname>', methods=['POST'])
@login_required
def follow_user(nickname):
    """Оформить подписку на пользователя. Если подписка взаимная — они автоматически станут друзьями."""
    if current_user.nickname == nickname:
        flash('Вы не можете подписаться на самого себя!')
        return redirect(url_for('auth.user_profile', nickname=nickname))

    db_sess = db_session.create_session()
    try:
        target_user = db_sess.query(User).filter(User.nickname == nickname).first()
        if not target_user:
            abort(404)

        # Подгружаем объекты в текущую сессию для безопасного изменения отношений
        me = db_sess.get(User, current_user.id)

        if me.is_following(target_user):
            flash(f'Вы уже подписаны на @{target_user.nickname}.')
        else:
            me.follow(target_user)
            db_sess.commit()
            if me.is_friend_with(target_user):
                flash(f'Ура! Вы и @{target_user.nickname} теперь друзья!')
            else:
                flash(f'Вы успешно подписались на @{target_user.nickname}.')

        return redirect(url_for('auth.user_profile', nickname=nickname))
    finally:
        db_sess.close()


@social_bp.route('/unfollow/<string:nickname>', methods=['POST'])
@login_required
def unfollow_user(nickname):
    """Отменить подписку на пользователя. Статус дружбы также автоматически разрушится."""
    db_sess = db_session.create_session()
    try:
        target_user = db_sess.query(User).filter(User.nickname == nickname).first()
        if not target_user:
            abort(404)

        me = db_sess.get(User, current_user.id)

        if not me.is_following(target_user):
            flash(f'Вы не были подписаны на @{target_user.nickname}.')
        else:
            me.unfollow(target_user)
            db_sess.commit()
            flash(f'Вы отменили подписку на @{target_user.nickname}.')

        return redirect(url_for('auth.user_profile', nickname=nickname))
    finally:
        db_sess.close()


@social_bp.route('/profile/<string:nickname>/friends_hub')
@login_required
def friends_hub(nickname):
    """Единая панель социального графа: списки друзей, подписчиков и ваших подписок."""
    db_sess = db_session.create_session()
    try:
        user = db_sess.query(User).filter(User.nickname == nickname).first()
        if not user:
            abort(404)

        # Проверка настроек приватности (0: Все, 1: Друзья, 2: Подписчики, 3: Никто)
        me = db_sess.get(User, current_user.id)
        is_owner = (user.id == me.id)

        if not is_owner and user.privacy_level == 3:
            abort(403)  # Скрыто от всех
        if not is_owner and user.privacy_level == 1 and not user.is_friend_with(me):
            abort(403)  # Скрыто для не-друзей
        if not is_owner and user.privacy_level == 2 and not user.is_followed_by(me):
            abort(403)  # Скрыто для не-подписчиков

        # Вычисляем списки через SQL-фильтры на основе взаимности
        all_following = user.followed.all()

        # Подписчики: те, у кого этот пользователь в списке подписок
        all_followers = db_sess.query(User).join(
            followers, followers.c.follower_id == User.id
        ).filter(followers.c.followed_id == user.id).all()

        # Друзья: пересечение (взаимные подписки)
        friends = [u for u in all_following if user.is_friend_with(u)]

        # Чистые подписчики (без взаимности)
        just_followers = [u for u in all_followers if u not in friends]

        # Чистые подписки (без взаимности)
        just_following = [u for u in all_following if u not in friends]

        return render_template(
            'friends_hub.html',
            title=f'Социальный граф @{user.nickname}',
            user=user,
            friends=friends,
            followers=just_followers,
            following=just_following
        )
    finally:
        db_sess.close()
