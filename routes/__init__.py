from functools import wraps
from flask import abort
from flask_login import login_required, current_user

ROLE_USER = 0
ROLE_VERIFIED = 1
ROLE_ADMIN_MEDIA = 2
ROLE_ADMIN = 3
ROLE_CHIEF_ADMIN = 4

def role_required(min_level):
    """Декоратор для ограничения доступа к маршрутам на основе иерархии ролей Luma."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role_level < min_level:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
