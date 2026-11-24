
import xml.etree.ElementTree as ET
import re
from svgpathtools import parse_path


# SVG elements whose children use their own coordinate systems
# and are not directly drawn in the main SVG viewport.
DEFINITION_TAGS = {
    "defs",
    "pattern",
    "marker",
    "clipPath",
    "mask",
    "symbol"
}


def get_number(value, default=None):
    """Extract the first numeric value from an SVG attribute."""

    if value is None:
        return default

    match = re.match(
        r"^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)",
        str(value)
    )

    return float(match.group(1)) if match else default


def is_inside_definition(element, parent_map):
    """Check whether an element belongs to a non-rendered definition."""

    current = element

    while current in parent_map:
        current = parent_map[current]

        tag = current.tag.split("}")[-1]

        if tag in DEFINITION_TAGS:
            return True

    return False


def validate_svg(svg):
    """
    Perform six programmatic SVG validation checks.

    1. Valid XML
    2. Elements inside viewBox
    3. SVG title exists
    4. At least three text labels
    5. At least one animation
    6. At least three graphical elements

    Path geometry is checked using svgpathtools.
    Paths inside SVG definitions are excluded because
    they use separate coordinate systems.
    """

    checks = {}
    errors = []

    # CHECK 1: VALID XML

    try:
        root = ET.fromstring(svg)

        if root.tag.split("}")[-1] != "svg":
            raise ValueError("Root element must be SVG.")

        checks["valid_xml"] = True

    except Exception as error:

        failed_checks = {
            "valid_xml": False,
            "inside_viewbox": False,
            "has_title": False,
            "has_labels": False,
            "has_animation": False,
            "has_graphics": False
        }

        return {
            "valid": False,
            "passed": False,
            "checks": failed_checks,
            "errors": [f"Invalid SVG XML: {error}"]
        }

    # Build parent relationships for identifying definitions.

    parent_map = {
        child: parent
        for parent in root.iter()
        for child in parent
    }

    # CHECK 2: VIEWBOX BOUNDARY VALIDATION

    inside_viewbox = True

    try:

        viewbox = root.attrib.get("viewBox")

        if not viewbox:
            raise ValueError("SVG viewBox is missing.")

        values = [
            float(value)
            for value in viewbox.replace(",", " ").split()
        ]

        if len(values) != 4:
            raise ValueError(
                "viewBox must contain exactly four numbers."
            )

        min_x, min_y, width, height = values

        if width <= 0 or height <= 0:
            raise ValueError(
                "viewBox width and height must be positive."
            )

        max_x = min_x + width
        max_y = min_y + height

        tolerance = 1e-6

        def point_inside(x, y):
            return (
                min_x - tolerance <= x <= max_x + tolerance
                and min_y - tolerance <= y <= max_y + tolerance
            )

        def box_inside(left, top, right, bottom):
            return (
                left >= min_x - tolerance
                and top >= min_y - tolerance
                and right <= max_x + tolerance
                and bottom <= max_y + tolerance
            )

        for element in root.iter():

            tag = element.tag.split("}")[-1]

            # Reject transforms because this validator does not
            # calculate transformed coordinate matrices.

            if element.attrib.get("transform"):
                raise ValueError(
                    "Unsupported SVG transform detected. "
                    "Transformed coordinates require matrix calculations."
                )

            # Definition elements have their own coordinate systems.
            # Their geometry is not compared with the main viewBox.

            if is_inside_definition(element, parent_map):
                continue

            # RECTANGLE

            if tag == "rect":

                x = get_number(element.get("x"), 0)
                y = get_number(element.get("y"), 0)
                w = get_number(element.get("width"))
                h = get_number(element.get("height"))

                if w is None or h is None:
                    raise ValueError(
                        "Rectangle has unsupported or missing dimensions."
                    )

                if w < 0 or h < 0:
                    raise ValueError("Rectangle dimensions cannot be negative.")

                if not box_inside(x, y, x + w, y + h):
                    inside_viewbox = False

            # CIRCLE

            elif tag == "circle":

                cx = get_number(element.get("cx"), 0)
                cy = get_number(element.get("cy"), 0)
                r = get_number(element.get("r"))

                if r is None or r < 0:
                    raise ValueError("Circle has invalid radius.")

                if not box_inside(cx - r, cy - r, cx + r, cy + r):
                    inside_viewbox = False

            # ELLIPSE

            elif tag == "ellipse":

                cx = get_number(element.get("cx"), 0)
                cy = get_number(element.get("cy"), 0)
                rx = get_number(element.get("rx"))
                ry = get_number(element.get("ry"))

                if rx is None or ry is None or rx < 0 or ry < 0:
                    raise ValueError("Ellipse has invalid radii.")

                if not box_inside(cx - rx, cy - ry, cx + rx, cy + ry):
                    inside_viewbox = False

            # LINE

            elif tag == "line":

                x1 = get_number(element.get("x1"), 0)
                y1 = get_number(element.get("y1"), 0)
                x2 = get_number(element.get("x2"), 0)
                y2 = get_number(element.get("y2"), 0)

                if not (
                    point_inside(x1, y1)
                    and point_inside(x2, y2)
                ):
                    inside_viewbox = False

            # TEXT

            elif tag == "text":

                x = get_number(element.get("x"))
                y = get_number(element.get("y"))

                if x is not None and not min_x - tolerance <= x <= max_x + tolerance:
                    inside_viewbox = False

                if y is not None and not min_y - tolerance <= y <= max_y + tolerance:
                    inside_viewbox = False

            # POLYGON AND POLYLINE

            elif tag in ("polygon", "polyline"):

                points = element.get("points", "")

                numbers = [
                    float(number)
                    for number in re.findall(
                        r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?",
                        points
                    )
                ]

                if len(numbers) < 4 or len(numbers) % 2 != 0:
                    raise ValueError(
                        f"Invalid {tag} coordinate list."
                    )

                for i in range(0, len(numbers), 2):

                    px = numbers[i]
                    py = numbers[i + 1]

                    if not point_inside(px, py):
                        inside_viewbox = False
                        break

            # PATH: STRAIGHT LINES, QUADRATIC CURVES,
            # CUBIC CURVES AND ARC SEGMENTS

            elif tag == "path":

                path_data = element.get("d")

                if not path_data:
                    raise ValueError("SVG path has no d attribute.")

                try:
                    parsed_path = parse_path(path_data)

                    if len(parsed_path) == 0:
                        raise ValueError("SVG path contains no segments.")

                    path_min_x, path_max_x, path_min_y, path_max_y = (
                        parsed_path.bbox()
                    )

                except Exception as path_error:
                    raise ValueError(
                        f"Unable to validate SVG path: {path_error}"
                    )

                if not box_inside(
                    path_min_x,
                    path_min_y,
                    path_max_x,
                    path_max_y
                ):
                    inside_viewbox = False

            if not inside_viewbox:
                break

        checks["inside_viewbox"] = inside_viewbox

        if not inside_viewbox:
            errors.append(
                "One or more supported SVG elements extend "
                "outside the viewBox boundaries."
            )

    except Exception as error:

        checks["inside_viewbox"] = False

        errors.append(
            f"ViewBox validation failed: {error}"
        )

    # CHECK 3: TITLE EXISTS

    has_title = any(
        element.tag.split("}")[-1] == "title"
        and (element.text or "").strip()
        for element in root.iter()
    )

    checks["has_title"] = has_title

    if not has_title:
        errors.append(
            "SVG must contain a descriptive title."
        )

    # CHECK 4: AT LEAST THREE TEXT LABELS

    text_labels = [
        element
        for element in root.iter()
        if element.tag.split("}")[-1] == "text"
        and "".join(element.itertext()).strip()
    ]

    has_labels = len(text_labels) >= 3

    checks["has_labels"] = has_labels

    if not has_labels:
        errors.append(
            f"Only {len(text_labels)} text labels found. "
            "At least three text labels are required."
        )

    # CHECK 5: ANIMATION EXISTS

    animation_tags = {
        "animate",
        "animateTransform",
        "animateMotion",
        "set"
    }

    has_smil = any(
        element.tag.split("}")[-1] in animation_tags
        for element in root.iter()
    )

    has_css_animation = bool(
        re.search(r"@keyframes", svg, re.IGNORECASE)
        and re.search(r"animation\s*:", svg, re.IGNORECASE)
    )

    has_animation = has_smil or has_css_animation

    checks["has_animation"] = has_animation

    if not has_animation:
        errors.append(
            "SVG must contain at least one CSS or SMIL animation."
        )

    # CHECK 6: GRAPHICAL CONTENT

    graphical_tags = {
        "rect",
        "circle",
        "ellipse",
        "line",
        "polygon",
        "polyline",
        "path"
    }

    graphic_count = sum(
        1
        for element in root.iter()
        if element.tag.split("}")[-1] in graphical_tags
        and not is_inside_definition(element, parent_map)
    )

    has_graphics = graphic_count >= 3

    checks["has_graphics"] = has_graphics

    if not has_graphics:
        errors.append(
            f"Only {graphic_count} graphical elements found. "
            "At least three graphical elements are required."
        )

    # FINAL VALIDATION RESULT

    overall_result = all(checks.values())

    return {
        "valid": overall_result,
        "passed": overall_result,
        "checks": checks,
        "errors": errors
    }
