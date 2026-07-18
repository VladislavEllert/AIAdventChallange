"""Throwaway smoke-test file for AI-review Action (day 35.5, PR c: clean).

Not wired into the app. A small, correct, well-structured refactor-shaped
snippet — extracts a repeated calculation into a named helper — to verify
the review Action doesn't invent problems on clean code.
"""


def _rectangle_area(width: float, height: float) -> float:
    """Area of a rectangle, shared by the perimeter/area/ratio helpers below."""
    return width * height


def rectangle_perimeter(width: float, height: float) -> float:
    return 2 * (width + height)


def rectangle_area(width: float, height: float) -> float:
    return _rectangle_area(width, height)


def rectangle_aspect_ratio(width: float, height: float) -> float:
    if height == 0:
        raise ValueError("height must be non-zero")
    return width / height
