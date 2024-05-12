import os
import pathlib
import typing

from PIL import Image, UnidentifiedImageError
from sqlite_utils import Database
import tqdm

from .tint_colors import choose_tint_color


def get_file_paths_under(root="."):
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
            if f == ".DS_Store":
                continue

            yield dirpath / f


class ImageInfo(typing.TypedDict):
    path: pathlib.Path
    width: int
    height: int
    mtime: int
    tint_color: str


def get_info(path: pathlib.Path, mtime: int) -> ImageInfo | None:
    """
    Get information about a single image.
    """
    try:
        im = Image.open(path)
    except UnidentifiedImageError:
        return None

    tint_color = choose_tint_color(im)

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


def get_image_info(root: str, *, show_progress: bool = False) -> list[ImageInfo]:
    """
    Get info about all the images under ``root``.
    """
    db = Database("image_info.db")

    known_images = {}

    for row in db["images"].rows:
        row["path"] = pathlib.Path(row["path"])
        known_images[(row["path"], row["mtime"])] = row

    result: list[ImageInfo] = []

    paths = list(get_file_paths_under(root))

    if show_progress:
        paths = tqdm.tqdm(paths)

    for p in paths:
        mtime = os.path.getmtime(p)

        try:
            info = known_images[(p, mtime)]
        except KeyError:
            info = get_info(p, mtime)

        if info is not None:
            result.append(info)

    return result
