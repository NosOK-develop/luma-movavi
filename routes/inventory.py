from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from data import db_session
from data.inventory import InventoryItem, UserItem

inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/inventory')
@login_required
def user_inventory():
    """Просмотр инвентаря текущего аккаунта Luma v0.99.2.4"""
    db_sess = db_session.create_session()
    try:
        user_items = db_sess.query(UserItem).filter(UserItem.user_id == current_user.id).all()
        return render_template('inventory.html', title='Мой инвентарь', user_items=user_items)
    finally:
        db_sess.close()


@inventory_bp.route('/inventory/equip/<int:user_item_id>', methods=['POST'])
@login_required
def equip_item(user_item_id):
    """Надеть (экипировать) или снять предмет кастомизации."""
    db_sess = db_session.create_session()
    try:
        user_item = db_sess.query(UserItem).filter(
            UserItem.id == user_item_id,
            UserItem.user_id == current_user.id
        ).first()

        if not user_item:
            abort(404)

        if user_item.is_equipped:
            user_item.is_equipped = False
            flash(f'Предмет "{user_item.item.title}" успешно снят.')
        else:
            # Снимаем все другие предметы ЭТОГО ЖЕ ТИПА
            same_type_items = db_sess.query(UserItem).join(InventoryItem).filter(
                UserItem.user_id == current_user.id,
                InventoryItem.item_type == user_item.item.item_type
            ).all()
            for item in same_type_items:
                item.is_equipped = False

            user_item.is_equipped = True
            flash(f'Предмет "{user_item.item.title}" успешно активирован!')

        db_sess.commit()
        return redirect(url_for('inventory.user_inventory'))
    finally:
        db_sess.close()
