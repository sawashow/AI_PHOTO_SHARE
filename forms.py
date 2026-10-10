from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired, FileSize
from wtforms import PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Regexp

ALLOWED_IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif"]
MAX_IMAGE_BYTES = 5 * 1024 * 1024


class RegisterForm(FlaskForm):
    username = StringField(
        "ユーザー名",
        validators=[
            DataRequired(message="ユーザー名を入力してください。"),
            Regexp(
                r"^[A-Za-z0-9_]{1,50}$",
                message="ユーザー名は英数字とアンダースコアだけ、50文字以内で入力してください。",
            ),
        ],
    )
    email = StringField(
        "メールアドレス",
        validators=[
            DataRequired(message="メールアドレスを入力してください。"),
            Length(max=254, message="メールアドレスは254文字以内で入力してください。"),
            Email(
                message="メールアドレスの形式で入力してください。",
                check_deliverability=False,
            ),
        ],
    )
    password = PasswordField(
        "パスワード",
        validators=[
            DataRequired(message="パスワードを入力してください。"),
            Length(min=8, message="パスワードは8文字以上にしてください。"),
        ],
    )
    submit = SubmitField("登録する")

    def validate(self, extra_validators=None):
        if self.username.data:
            self.username.data = self.username.data.strip()
        if self.email.data:
            self.email.data = self.email.data.strip()
        return super().validate(extra_validators=extra_validators)


class LoginForm(FlaskForm):
    username = StringField(
        "ユーザー名",
        validators=[DataRequired(message="ユーザー名を入力してください。")],
    )
    password = PasswordField(
        "パスワード",
        validators=[DataRequired(message="パスワードを入力してください。")],
    )
    submit = SubmitField("ログイン")

    def validate(self, extra_validators=None):
        if self.username.data:
            self.username.data = self.username.data.strip()
        return super().validate(extra_validators=extra_validators)


class PostForm(FlaskForm):
    image = FileField(
        "写真",
        validators=[
            FileRequired(message="写真を選んでください。"),
            FileAllowed(
                ALLOWED_IMAGE_EXTENSIONS,
                message="写真は PNG、JPEG、GIF のどれかを選んでください。",
            ),
            FileSize(
                max_size=MAX_IMAGE_BYTES,
                message="写真は 5MB 以下にしてください。",
            ),
        ],
    )
    caption = TextAreaField(
        "キャプション",
        validators=[Length(max=200, message="キャプションは200文字以内で入力してください。")],
    )
    submit = SubmitField("投稿する")
