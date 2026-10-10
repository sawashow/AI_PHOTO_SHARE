from datetime import datetime
from pathlib import Path

from flask_login import UserMixin
from peewee import CharField, DateTimeField, ForeignKeyField, Model, SqliteDatabase

db = SqliteDatabase(
    Path(__file__).resolve().parent / "app.db",
    pragmas={"foreign_keys": 1},
)


class BaseModel(Model):
    class Meta:
        database = db


class User(UserMixin, BaseModel):
    username = CharField(max_length=50)
    username_normalized = CharField(max_length=50, unique=True)
    email = CharField(max_length=254)
    email_normalized = CharField(max_length=254, unique=True)
    password_hash = CharField(max_length=255)
    created_at = DateTimeField(default=datetime.now)


class Post(BaseModel):
    user = ForeignKeyField(User, backref="posts", on_delete="RESTRICT")
    image_filename = CharField(max_length=255, unique=True)
    caption = CharField(max_length=200, default="")
    created_at = DateTimeField(default=datetime.now)
