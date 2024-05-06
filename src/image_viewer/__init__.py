import os
import random
import time

from flask import Flask, current_app, render_template, request, send_file

from .image_info import get_image_info


def create_app(root: str) -> Flask:
    app = Flask(__name__)
    app.config["ROOT"] = root

    app.add_url_rule("/", view_func=index)
    app.add_url_rule("/image", view_func=send_image)

    return app


def index() -> str:
    root = current_app.config["ROOT"]

    max_images = request.args.get("max_images")
    if max_images is not None:
        max_images = int(max_images)

    t0 = time.time()
    image_info = sorted(
        get_image_info(root, max_images=max_images), key=lambda info: random.random()
    )
    t1 = time.time()

    return render_template("index.html", image_info=image_info, root=root, t=t1 - t0)


def send_image():
    path = request.args["path"]
    resp = send_file(os.path.abspath(path))
    resp.cache_control.max_age = 3153600
    del resp.cache_control.no_cache
    resp.cache_control.public = True
    return resp
