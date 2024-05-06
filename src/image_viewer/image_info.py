import concurrent.futures
import itertools
import os
import pathlib
import typing

from PIL import Image, UnidentifiedImageError
from sqlite_utils import Database

from .tint_colors import choose_tint_color_for_file


def get_file_paths_under(root=".", *, suffix=""):
    """
    Generates the absolute paths to every matching file under ``root``.
    """
    root = pathlib.Path(root)

    if root.exists() and not root.is_dir():
        raise ValueError(f"Cannot find files under file: {root!r}")

    if not root.is_dir():
        raise FileNotFoundError(root)

    for dirpath, _, filenames in root.walk():
        for f in filenames:
            p = dirpath / f

            if f == ".DS_Store":
                continue

            if p.is_file() and f.lower().endswith(suffix):
                yield p


def get_tint_color(path: str, mtime: int) -> str:
    r, g, b = choose_tint_color_for_file(path)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


class ImageInfo(typing.TypedDict):
    path: pathlib.Path
    width: int
    height: int
    mtime: int
    tint_color: str
    tint_color_is_new: bool


def get_info(
    known_images: dict[tuple[str, int], str], path: pathlib.Path
) -> ImageInfo | None:
    try:
        im = Image.open(path)
    except UnidentifiedImageError:
        return None

    mtime = os.path.getmtime(path)

    try:
        tint_color = known_images[(str(path), mtime)]
        tint_color_is_new = False
    except KeyError:
        tint_color = get_tint_color(path, mtime)
        tint_color_is_new = True

    return ImageInfo(
        path=path,
        width=im.width,
        height=im.height,
        mtime=mtime,
        tint_color=tint_color,
        tint_color_is_new=tint_color_is_new,
    )


def get_image_info(root: str, *, max_images: int | None = None) -> list[ImageInfo]:
    db = Database("image_info.db")

    known_images = {
        (row["path"], row["mtime"]): row["tint_color"] for row in db["images"].rows
    }

    result: list[ImageInfo] = []

    if max_images is None:
        paths = get_file_paths_under(root)
    else:
        paths = itertools.islice(get_file_paths_under(root), max_images)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(get_info, known_images, p)
            for p in paths
        }

        for fut in concurrent.futures.as_completed(futures):
            if fut.result() is not None:
                result.append(fut.result())

    db["images"].upsert_all(
        [
            {
                "path": str(info["path"]),
                "mtime": info["mtime"],
                "tint_color": info["tint_color"],
            }
            for info in result
            if info["tint_color_is_new"]
        ],
        pk="path",
    )

    return result
