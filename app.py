from flask import Flask, render_template

from models import Post, User, db

app = Flask(__name__)


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
