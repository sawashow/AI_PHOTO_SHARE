import logging
import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from flask import (
    Flask,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from peewee import DatabaseError, IntegrityError
from PIL import Image
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.security import check_password_hash, generate_password_hash

from forms import MAX_IMAGE_BYTES, LoginForm, PostForm, RegisterForm
from models import Post, User, db

BASE_DIR = Path(__file__).resolve().parent
POST_UPLOAD_DIR = BASE_DIR / "uploads" / "posts"
IMAGE_FORMAT_EXTENSIONS = {"PNG": "png", "JPEG": "jpg", "GIF": "gif"}

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY が .env にありません。")
app.config["SECRET_KEY"] = secret_key
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = BASE_DIR / "flask_session"
# 写真 5MB に、キャプションや CSRF トークンなどフォームの残りの分を足した上限
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_BYTES + 64 * 1024

Session(app)
CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = None
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
    posts = list(
        Post.select(Post, User)
        .join(User)
        .order_by(Post.created_at.desc(), Post.id.desc())
    )
    return render_template("index.html", posts=posts)


@app.route("/posts/new")
@login_required
def new_post():
    return render_template("post_new.html", form=PostForm())


@app.route("/posts", methods=["POST"])
@login_required
def create_post():
    form = PostForm()
    if not form.validate_on_submit():
        return render_template("post_new.html", form=form)

    extension = detect_image_extension(form.image.data)
    if extension is None:
        form.image.errors.append(
            "写真として読み込めませんでした。PNG、JPEG、GIF の画像を選んでください。"
        )
        return render_template("post_new.html", form=form)

    filename = f"{uuid4().hex}.{extension}"
    saved_path = POST_UPLOAD_DIR / filename
    try:
        form.image.data.save(saved_path)
    except OSError:
        logger.exception("写真ファイルを保存できませんでした: %s", saved_path)
        remove_saved_file(saved_path)
        form.image.errors.append("写真を保存できませんでした。もう一度試してください。")
        return render_template("post_new.html", form=form)

    try:
        Post.create(
            user=current_user.id,
            image_filename=filename,
            caption=form.caption.data or "",
        )
    except DatabaseError:
        logger.exception("投稿をデータベースに保存できませんでした。")
        remove_saved_file(saved_path)
        form.image.errors.append("投稿を保存できませんでした。もう一度試してください。")
        return render_template("post_new.html", form=form)

    return redirect(url_for("index"))


@app.route("/uploads/posts/<filename>")
def post_image(filename):
    response = send_from_directory(POST_UPLOAD_DIR, filename)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.errorhandler(RequestEntityTooLarge)
def request_too_large(error):
    if request.endpoint != "create_post" or not current_user.is_authenticated:
        return error
    form = PostForm(formdata=None)
    form.image.errors = ["写真は 5MB 以下にしてください。"]
    return render_template("post_new.html", form=form), 413


def detect_image_extension(file_storage):
    stream = file_storage.stream
    try:
        with Image.open(stream) as image:
            image.verify()
            image_format = image.format
    except Exception:
        logger.info("画像として読み込めないファイルを拒否しました。", exc_info=True)
        return None
    finally:
        stream.seek(0)
    return IMAGE_FORMAT_EXTENSIONS.get(image_format)


def remove_saved_file(path):
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("後片付けで写真ファイルを削除できませんでした: %s", path)


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
POST_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
