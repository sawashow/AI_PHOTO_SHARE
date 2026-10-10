import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, url_for
from flask_login import LoginManager, current_user, login_user, logout_user
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from peewee import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from forms import LoginForm, RegisterForm
from models import Post, User, db

load_dotenv(Path(__file__).resolve().parent / ".env")

app = Flask(__name__)
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY が .env にありません。")
app.config["SECRET_KEY"] = secret_key
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = Path(__file__).resolve().parent / "flask_session"

Session(app)
CSRFProtect(app)
login_manager = LoginManager(app)
logger = logging.getLogger(__name__)


@login_manager.user_loader
def load_user(user_id):
    try:
        user_pk = int(user_id)
    except (TypeError, ValueError):
        return None
    return User.get_or_none(User.id == user_pk)


@app.before_request
def open_db():
    if db.is_closed():
        db.connect()


@app.teardown_request
def close_db(error):
    if not db.is_closed():
        db.close()
    return error


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        username_normalized = username.casefold()
        email_normalized = email.casefold()
        if User.get_or_none(User.username_normalized == username_normalized):
            form.username.errors.append("このユーザー名は既に使われています。")
        elif User.get_or_none(User.email_normalized == email_normalized):
            form.email.errors.append("このメールアドレスは既に使われています。")
        else:
            try:
                User.create(
                    username=username,
                    username_normalized=username_normalized,
                    email=email,
                    email_normalized=email_normalized,
                    password_hash=generate_password_hash(form.password.data),
                )
            except IntegrityError:
                logger.warning("ユーザー登録がユニーク制約で失敗しました。")
                form.username.errors.append(
                    "このユーザー名またはメールアドレスは既に使われています。"
                )
            else:
                return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    auth_error = None
    if form.validate_on_submit():
        user = User.get_or_none(
            User.username_normalized == form.username.data.casefold()
        )
        password = form.password.data
        if user is None or not check_password_hash(user.password_hash, password):
            auth_error = "ユーザー名またはパスワードが違います。"
        else:
            login_user(user)
            return redirect(url_for("index"))
    return render_template("login.html", form=form, auth_error=auth_error)


@app.route("/logout", methods=["POST"])
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for("index"))


def init_db():
    db.connect(reuse_if_open=True)
    try:
        db.create_tables([User, Post])
    finally:
        if not db.is_closed():
            db.close()


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
