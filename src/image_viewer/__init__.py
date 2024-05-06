import os
import random

from flask import Flask, current_app, render_template, request, send_file

from .image_info import get_image_info


def create_app() -> Flask:
    root = os.environ["ROOT"]

    app = Flask(__name__)
    app.config["ROOT"] = root

    app.add_url_rule("/", view_func=index)
    app.add_url_rule("/image", view_func=send_image)

    get_image_info(root, show_progress=True)

    return app


def index() -> str:
    root = current_app.config["ROOT"]

    image_info = sorted(get_image_info(root), key=lambda info: random.random())

    return render_template("index.html", image_info=image_info, root=root)


def send_image():
    path = request.args["path"]
    resp = send_file(os.path.abspath(path))
    resp.cache_control.max_age = 3153600
    del resp.cache_control.no_cache
    resp.cache_control.public = True
    return resp
