from flask import Blueprint, render_template, request, redirect, abort, session
from flask_login import current_user
from data import db_session
from data.users import User

# ИСПРАВЛЕНИЕ: ставим точку перед именем пакета для локального импорта из __init__.py
from . import role_required, ROLE_ADMIN, ROLE_CHIEF_ADMIN

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/secret-cli')
@role_required(ROLE_CHIEF_ADMIN)
def admin_cli_page():
    return render_template('admin_cli.html', title="Console")

@admin_bp.route('/admin/users')
@role_required(ROLE_ADMIN)
def admin_users_list():
    db_sess = db_session.create_session()
    try:
        all_users = db_sess.query(User).order_by(User.role_level.desc()).all()
        return render_template('admin_users.html', title='Управление пользователями', sorted_users=all_users)
    finally:
        db_sess.close()


@admin_bp.route('/admin/users/<int:target_user_id>/change_role', methods=['POST'])
@role_required(ROLE_ADMIN)
def change_user_role(target_user_id):
    new_level = request.form.get('role_level', type=int)
    if new_level is None or new_level < 0 or new_level > 4:
        return redirect('/admin/users')

    db_sess = db_session.create_session()
    try:
        target_user = db_sess.get(User, target_user_id)
        if not target_user:
            abort(404)

        if target_user.role_level == ROLE_CHIEF_ADMIN and current_user.role_level < ROLE_CHIEF_ADMIN:
            abort(403)
        if new_level == ROLE_CHIEF_ADMIN and current_user.role_level < ROLE_CHIEF_ADMIN:
            abort(403)
        if target_user.id == current_user.id:
            abort(400)

        target_user.role_level = new_level
        db_sess.commit()

        session['role_updated'] = True
        return redirect('/admin/users')
    finally:
        db_sess.close()
