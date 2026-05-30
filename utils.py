import os
import uuid
from PIL import Image

# Временный объект-заглушка для хранения пути. Напрямую импортировать app.config нельзя.
UPLOAD_FOLDER = os.path.join('static')


def compress_and_save_image(file):
    """Конвертирует изображение в WebP и сжимает его для экономии места на диске Luma"""
    if file.filename and file.filename.startswith('._'):
        return "/static/images/default_avatar.png"
    try:
        filename = f"{uuid.uuid4().hex}.webp"
        filepath = os.path.join(UPLOAD_FOLDER, 'images', filename)

        img = Image.open(file)
        img.thumbnail((1280, 1280))
        img.save(filepath, 'WEBP', quality=75)
        return f"/static/images/{filename}"
    except Exception as e:
        print(f"[ERROR] Ошибка сжатия картинки: {e}")
        return "/static/images/default_avatar.png"


def compress_video_thumbnail(file):
    """Сжимает обложку видео в WebP 16:9 для Luma Video"""
    if file.filename and file.filename.startswith('._'):
        return "/static/thumbnails/default_video.png"
    try:
        filename = f"{uuid.uuid4().hex}.webp"
        filepath = os.path.join(UPLOAD_FOLDER, 'thumbnails', filename)

        img = Image.open(file)
        img.thumbnail((854, 480))
        img.save(filepath, 'WEBP', quality=70)
        return f"/static/thumbnails/{filename}"
    except Exception as e:
        print(f"[ERROR] Ошибка сжатия обложки: {e}")
        return "/static/thumbnails/default_video.png"


def compress_channel_banner(file):
    """Сжимает баннер канала в WebP с сохранением пропорций 16:9 или широкого формата."""
    if file.filename and file.filename.startswith('._'):
        return "/static/images/default_channel_banner.png"
    try:
        filename = f"banner_{uuid.uuid4().hex}.webp"
        filepath = os.path.join(UPLOAD_FOLDER, 'images', filename)

        img = Image.open(file)
        img.thumbnail((1920, 1080))  # Оптимальное FullHD разрешение для десктопных баннеров
        img.save(filepath, 'WEBP', quality=75)
        return f"/static/images/{filename}"
    except Exception as e:
        print(f"[ERROR] Ошибка сжатия баннера канала: {e}")
        return "/static/images/default_channel_banner.png"


def compress_player_icon(file):
    """Сжимает вотермарку/иконку плеера в компактный квадратный WebP."""
    if file.filename and file.filename.startswith('._'):
        return "/static/images/default_player_icon.png"
    try:
        filename = f"picon_{uuid.uuid4().hex}.webp"
        filepath = os.path.join(UPLOAD_FOLDER, 'images', filename)

        img = Image.open(file)
        img.thumbnail((128, 128))  # Маленький размер для иконки внутри видеоплеера
        img.save(filepath, 'WEBP', quality=85)
        return f"/static/images/{filename}"
    except Exception as e:
        print(f"[ERROR] Ошибка сжатия иконки плеера: {e}")
        return "/static/images/default_player_icon.png"


import cv2


def generate_video_first_frame(video_path):
    """Извлекает первый кадр видео в формате WebP, если обложка не загружена (v0.98.4.3)"""
    try:
        thumb_filename = f"thumb_{uuid.uuid4().hex}.webp"
        thumb_filepath = os.path.join(UPLOAD_FOLDER, 'thumbnails', thumb_filename)

        # Открываем видеофайл через OpenCV
        cap = cv2.VideoCapture(video_path)
        success, frame = cap.read()
        if success:
            # Сжимаем и сохраняем первый кадр в WebP
            cv2.imwrite(thumb_filepath, frame, [int(cv2.IMWRITE_WEBP_QUALITY), 70])
            cap.release()
            return f"/static/thumbnails/{thumb_filename}"
        cap.release()
    except Exception as e:
        print(f"[ERROR] Ошибка генерации первого кадра: {e}")
    return "/static/thumbnails/default_video.png"
