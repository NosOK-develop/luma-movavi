import datetime

import markdown
from flask import Blueprint, render_template, redirect, jsonify
from flask_login import login_required, current_user

from data import db_session
from data.posts import Post
from forms.posts import PostForm

post_bp = Blueprint('post', __name__)

@post_bp.route('/post/create', methods=['GET', 'POST'])
@login_required
def post_create():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, text=markdown.markdown(form.text.data), author=current_user, created_at=datetime.datetime.now())
        db_sess = db_session.create_session()
        db_sess.add(post)
        db_sess.commit()
        return redirect(f'/profile/{current_user.nickname}')
    return render_template('create_post.html', form=form)

@post_bp.route('/post/<id>', methods=['GET', 'POST'])
@login_required
def post(id):
    db_sess = db_session.create_session()
    post = db_sess.query(Post).get(id)
    return render_template('post.html', post=post)

@post_bp.route('/api/post/delete/<id>')
@login_required
def delete_post(id):
    db_sess = db_session.create_session()
    post = db_sess.query(Post).get(id)
    db_sess.delete(post)
    db_sess.commit()
    return redirect('/home')
