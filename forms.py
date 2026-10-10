from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Regexp


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
