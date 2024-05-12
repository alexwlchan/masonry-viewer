"""
See https://alexwlchan.net/2019/finding-tint-colours-with-k-means/
https://github.com/alexwlchan/docstore/blob/main/src/docstore/tint_colors.py
"""

import colorsys
import typing

from PIL import Image
from sklearn.cluster import KMeans
import wcag_contrast_ratio as contrast


Color: typing.TypeAlias = tuple[float, float, float]


def get_dominant_colours(im: Image, *, count: int) -> list[Color]:
    """
    Return a list of the dominant RGB colours in the image ``im``.

    :param im: An image as read by Pillow.
    :param count: Number of dominant colors to find.

    """
    # Resizing means less pixels to handle, so the *k*-means clustering converges
    # faster.  Small details are lost, but the main details will be preserved.
    im = im.resize((100, 100))

    # Ensure the image is RGB, and use RGB values in [0, 1] for consistency
    # with operations elsewhere.
    im = im.convert("RGB")

    colors = [(r / 255, g / 255, b / 255) for (r, g, b) in im.getdata()]

    # /Users/alexwlchan/textfiles/Attachments/2024/Screenshot 2024-02-01 at 08.01.10.png
    # gets negative numbers here!

    # /Users/alexwlchan/textfiles/Attachments/2023/buildkite-architecture.graffle/image4.png
    # gets >1 here!
    return [
        tuple(min(max(component, 0), 1) for component in c)
        for c in KMeans(n_clusters=count).fit(colors).cluster_centers_
    ]


def choose_best_tint_color(
    dominant_colors: list[Color], background_color: Color
) -> Color:
    """
    Given a list of dominant RGB colors and a background color, choose
    the color which will look best against this background.
    """
    # The minimum contrast ratio for text and background to meet WCAG AA
    # is 4.5:1, so discard any dominant colours with a lower contrast.
    sufficient_contrast_colors = [
        col for col in dominant_colors if contrast.rgb(col, background_color) >= 4.5
    ]

    # If none of the dominant colours meet WCAG AA with the background,
    # try again with black and white -- every colour in the RGB space
    # has a contrast ratio of 4.5:1 with at least one of these, so we'll
    # get a tint colour, even if it's not a good one.
    #
    # Note: you could modify the dominant colours until one of them
    # has sufficient contrast, but that's omitted here because it adds
    # a lot of complexity for a relatively unusual case.
    if not sufficient_contrast_colors:
        return choose_best_tint_color(
            dominant_colors=dominant_colors + [(0, 0, 0), (1, 1, 1)],
            background_color=background_color,
        )

    # Of the colours with sufficient contrast, pick the one with the
    # closest brightness (in the HSV colour space) to the background
    # colour.  This means we don't get very dark or very light colours,
    # but more bright, vibrant colours.
    hsv_background = colorsys.rgb_to_hsv(*background_color)
    hsv_candidates = {
        tuple(rgb_col): colorsys.rgb_to_hsv(*rgb_col)
        for rgb_col in sufficient_contrast_colors
    }

    candidates_by_brightness_diff = {
        rgb_col: abs(hsv_col[2] - hsv_background[2])
        for rgb_col, hsv_col in hsv_candidates.items()
    }

    rgb_choice, _ = min(candidates_by_brightness_diff.items(), key=lambda t: t[1])

    assert rgb_choice in dominant_colors
    return rgb_choice


def choose_tint_color(im: Image) -> Color:
    """
    Given an image, choose a single color based on the colors in the
    image that will look good against a black background.
    """
    dominant_colors = get_dominant_colours(im, count=16)
    r, g, b = choose_best_tint_color(dominant_colors, background_color=(0, 0, 0))
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
