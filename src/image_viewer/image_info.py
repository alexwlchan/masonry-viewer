import concurrent.futures
import itertools
import os
import pathlib
import typing

from PIL import Image, UnidentifiedImageError
from sqlite_utils import Database
import tqdm

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


def get_info(
    known_images: dict[tuple[str, int], str], path: pathlib.Path
) -> ImageInfo | None:
    mtime = os.path.getmtime(path)

    try:
        return known_images[(str(path), mtime)]
    except KeyError:
        pass

    tint_color = get_tint_color(path, mtime)

    try:
        im = Image.open(path)
    except UnidentifiedImageError:
        return None

    info = ImageInfo(
        path=path,
        width=im.width,
        height=im.height,
        mtime=mtime,
        tint_color=tint_color,
    )

    db = Database("image_info.db")
    db["images"].upsert(
        {
            "path": str(path),
            "mtime": mtime,
            "width": info["width"],
            "height": info["height"],
            "tint_color": info["tint_color"],
        },
        pk="path",
    )

    return info


def get_image_info(root: str, *, max_images: int | None = None) -> list[ImageInfo]:
    db = Database("image_info.db")

    import time
    t0 = time.time()
    known_images = {
        (row["path"], row["mtime"]): row for row in db["images"].rows
    }
    t1 = time.time(); print(t1 - t0); t0 = t1

    result: list[ImageInfo] = []

    if max_images is None:
        paths = get_file_paths_under(root)
    else:
        paths = itertools.islice(get_file_paths_under(root), max_images)

    paths = list(paths)
    missing_paths = set(paths) - set(p for p, _ in known_images.keys())

    if len(missing_paths) > 25:
        for p in tqdm.tqdm(paths):
            result.append(get_info(known_images, p))
    else:
        for p in paths:
            result.append(get_info(known_images, p))

    t1 = time.time(); print(t1 - t0); t0 = t1

    return result
