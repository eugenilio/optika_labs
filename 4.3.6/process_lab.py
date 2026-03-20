from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, log10, sqrt
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "lab-data.csv"
GEOMETRIC_IMAGE_SCALE_CM = 5.0


def parse_scalar(raw: str) -> float | int | str:
    raw = raw.strip()
    try:
        value = float(raw)
    except ValueError:
        return raw
    return int(value) if value.is_integer() else value


def parse_data(path: Path) -> tuple[dict[str, object], dict[str, list[dict[str, object]]]]:
    globals_data: dict[str, object] = {}
    tables: dict[str, list[dict[str, object]]] = {}
    section = "spectrum"
    header: list[str] | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            header = None
            continue
        if "=" in line and "," not in line:
            key, value = [part.strip() for part in line.split("=", 1)]
            globals_data[key] = parse_scalar(value)
            continue
        items = [item.strip() for item in line.split(",")]
        if header is None:
            header = items
            tables[section] = []
        else:
            row = {name: parse_scalar(value) for name, value in zip(header, items)}
            tables[section].append(row)

    return globals_data, tables


GLOBALS, TABLES = parse_data(DATA_PATH)
LAMBDA_MM = float(GLOBALS["lambda_nm"]) * 1e-6
L_MM = float(GLOBALS["L_mm"])
L_ERROR_MM = float(GLOBALS["L_error_mm"])
A_MM = float(GLOBALS["a_mm"])
A_ERROR_MM = float(GLOBALS["a_error_mm"])
B_MM = float(GLOBALS["b_mm"])
B_ERROR_MM = float(GLOBALS["b_error_mm"])


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ):
        path = Path(name)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def rel_error(*pairs: tuple[float, float]) -> float:
    total = 0.0
    for value, error in pairs:
        if value == 0:
            continue
        total += (error / value) ** 2
    return sqrt(total)


@dataclass
class SpectrumResult:
    cassette: str
    X_mm: float
    X_error_mm: float
    intervals: int

    @property
    def x_mm(self) -> float:
        return self.X_mm / self.intervals

    @property
    def x_error_mm(self) -> float:
        return self.X_error_mm / self.intervals

    @property
    def d_mm(self) -> float:
        return LAMBDA_MM * L_MM / self.x_mm

    @property
    def d_error_mm(self) -> float:
        return self.d_mm * rel_error((L_MM, L_ERROR_MM), (self.x_mm, self.x_error_mm))

    @property
    def talbot_mm(self) -> float:
        return 2.0 * self.d_mm * self.d_mm / LAMBDA_MM


@dataclass
class LensResult:
    cassette: str
    length_mm: float
    length_error_mm: float
    marked_points: int

    @property
    def intervals(self) -> int:
        return self.marked_points - 1

    @property
    def D_mm(self) -> float:
        return self.length_mm / self.intervals

    @property
    def D_error_mm(self) -> float:
        return self.length_error_mm / self.intervals

    @property
    def d_mm(self) -> float:
        return self.D_mm * A_MM / B_MM

    @property
    def d_error_mm(self) -> float:
        return self.d_mm * rel_error(
            (self.D_mm, self.D_error_mm),
            (A_MM, A_ERROR_MM),
            (B_MM, B_ERROR_MM),
        )


@dataclass
class SelfRepPoint:
    observation_index: int
    reading_cm: float
    reading_error_cm: float

    @property
    def z_mm(self) -> float:
        return (GEOMETRIC_IMAGE_SCALE_CM - self.reading_cm) * 10.0

    @property
    def z_error_mm(self) -> float:
        return self.reading_error_cm * 10.0


@dataclass
class SelfRepFit:
    cassette: str
    slope_mm: float
    slope_error_mm: float
    intercept_mm: float
    intercept_error_mm: float
    r_squared: float

    @property
    def d_mm(self) -> float:
        return sqrt(self.slope_mm * LAMBDA_MM / 2.0)

    @property
    def d_error_mm(self) -> float:
        return self.d_mm * 0.5 * self.slope_error_mm / self.slope_mm


SPECTRUM = [
    SpectrumResult(
        cassette=str(row["cassette"]),
        X_mm=float(row["X_mm"]),
        X_error_mm=float(row["X_error_mm"]),
        intervals=int(row["n"]),
    )
    for row in TABLES["spectrum"]
]
SPECTRUM_BY_CASSETTE = {point.cassette: point for point in SPECTRUM}

LENS = [
    LensResult(
        cassette=str(row["cassette"]),
        length_mm=float(row["length_mm"]),
        length_error_mm=float(row["length_error_mm"]),
        marked_points=int(row["marked_points"]),
    )
    for row in TABLES["task_7_lens_image"]
]

SELF_REP_RAW: dict[str, list[SelfRepPoint]] = {}
for row in TABLES["task_9_self_reproduction"]:
    SELF_REP_RAW.setdefault(str(row["cassette"]), []).append(
        SelfRepPoint(
            observation_index=int(row["order"]),
            reading_cm=float(row["raw_dist_cm"]),
            reading_error_cm=float(row["dist_error_cm"]),
        )
    )


def fit_self_rep_line(cassette: str) -> SelfRepFit:
    points = SELF_REP_RAW[cassette]
    x_values = [point.observation_index for point in points]
    y_values = [point.z_mm for point in points]
    count = len(points)
    x_mean = sum(x_values) / count
    y_mean = sum(y_values) / count
    sxx = sum((x - x_mean) ** 2 for x in x_values)
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    slope = sxy / sxx
    intercept = y_mean - slope * x_mean
    residuals = [y - (slope * x + intercept) for x, y in zip(x_values, y_values)]
    rss = sum(residual * residual for residual in residuals)
    tss = sum((y - y_mean) ** 2 for y in y_values)
    if count > 2:
        variance = rss / (count - 2)
        slope_error = sqrt(variance / sxx)
        intercept_error = sqrt(variance * (1.0 / count + x_mean * x_mean / sxx))
    else:
        slope_error = 0.0
        intercept_error = 0.0
    r_squared = 1.0 - rss / tss if tss else 1.0
    return SelfRepFit(
        cassette=cassette,
        slope_mm=slope,
        slope_error_mm=slope_error,
        intercept_mm=intercept,
        intercept_error_mm=intercept_error,
        r_squared=r_squared,
    )


SELF_REP_FITS = {cassette: fit_self_rep_line(cassette) for cassette in ("K3", "K4", "K5")}


def map_x(x: float, left: int, right: int, x0: float, x1: float) -> int:
    return int(left + (x - x0) / (x1 - x0) * (right - left))


def map_y(y: float, top: int, bottom: int, y0: float, y1: float) -> int:
    return int(bottom - (y - y0) / (y1 - y0) * (bottom - top))


def nice_step(span: float, target_ticks: int = 4) -> float:
    raw = span / max(target_ticks, 1)
    exponent = floor(log10(raw))
    base = 10 ** exponent
    for factor in (1, 2, 5, 10):
        step = factor * base
        if step >= raw:
            return step
    return 10 * base


def build_y_ticks(y_max: float) -> tuple[list[float], float]:
    step = nice_step(y_max)
    top = step * ceil(y_max / step)
    ticks = [index * step for index in range(int(top / step) + 1)]
    return ticks, top


class PlotStyle:
    def __init__(self, scale: int) -> None:
        self.scale = scale
        self.font = load_font(14 * scale)
        self.small_font = load_font(12 * scale)
        self.title_font = load_font(18 * scale)
        self.axis_color = "#222222"
        self.grid_color = "#d7dbe0"
        self.line_color = "#8a8a8a"
        self.bg_color = "white"
        self.marker_fill = "white"


def draw_errorbar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    err: int,
    color: str,
    width: int,
    cap: int,
) -> None:
    draw.line((x, y - err, x, y + err), fill=color, width=width)
    draw.line((x - cap, y - err, x + cap, y - err), fill=color, width=width)
    draw.line((x - cap, y + err, x + cap, y + err), fill=color, width=width)


def draw_axes(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    x_ticks: list[int],
    y_ticks: list[float],
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    x_label: str,
    y_label: str,
    style: PlotStyle,
    show_y_labels: bool = True,
) -> None:
    left, top, right, bottom = box
    axis_width = max(2, style.scale)
    tick_width = max(1, style.scale)
    tick_len = 5 * style.scale

    for tick in y_ticks:
        py = map_y(tick, top, bottom, y_range[0], y_range[1])
        draw.line((left, py, right, py), fill=style.grid_color, width=tick_width)
        draw.line((left - tick_len, py, left, py), fill=style.axis_color, width=tick_width)
        if show_y_labels:
            label = f"{tick:.1f}".rstrip("0").rstrip(".")
            tw = draw.textlength(label, font=style.small_font)
            draw.text((left - 10 * style.scale - tw, py - 7 * style.scale), label, font=style.small_font, fill=style.axis_color)

    for tick in x_ticks:
        px = map_x(tick, left, right, x_range[0], x_range[1])
        draw.line((px, bottom, px, bottom + tick_len), fill=style.axis_color, width=tick_width)
        label = str(tick)
        tw = draw.textlength(label, font=style.small_font)
        draw.text((px - tw / 2, bottom + 10 * style.scale), label, font=style.small_font, fill=style.axis_color)

    draw.line((left, bottom, right, bottom), fill=style.axis_color, width=axis_width)
    draw.line((left, top, left, bottom), fill=style.axis_color, width=axis_width)

    draw.text((right - 8 * style.scale, bottom + 34 * style.scale), x_label, font=style.font, fill=style.axis_color)
    draw.text((left - 2 * style.scale, top - 18 * style.scale), y_label, font=style.font, fill=style.axis_color)


def save_supersampled(image: Image.Image, size: tuple[int, int], path: Path) -> None:
    image.resize(size, Image.Resampling.LANCZOS).save(path)


def make_all_self_rep_points_plot() -> None:
    size = (1500, 520)
    scale = 3
    style = PlotStyle(scale)
    image = Image.new("RGB", (size[0] * scale, size[1] * scale), style.bg_color)
    draw = ImageDraw.Draw(image)
    colors = {"K3": "#1f77b4", "K4": "#d62728", "K5": "#2ca02c"}
    boxes = {
        "K3": (80 * scale, 70 * scale, 465 * scale, 430 * scale),
        "K4": (555 * scale, 70 * scale, 940 * scale, 430 * scale),
        "K5": (1030 * scale, 70 * scale, 1415 * scale, 430 * scale),
    }

    for cassette in ("K3", "K4", "K5"):
        left, top, right, bottom = boxes[cassette]
        title_width = draw.textlength(cassette, font=style.title_font)
        draw.text(((left + right - title_width) / 2, top - 42 * scale), cassette, font=style.title_font, fill="black")
        points = SELF_REP_RAW[cassette]
        fit = SELF_REP_FITS[cassette]
        x_values = [point.observation_index for point in points]
        y_ticks, y_top = build_y_ticks(max(point.z_mm + point.z_error_mm for point in points) * 1.05)
        x_range = (min(x_values) - 0.35, max(x_values) + 0.35)
        y_range = (0.0, y_top)
        draw_axes(
            draw,
            (left, top, right, bottom),
            x_values,
            y_ticks,
            x_range,
            y_range,
            "N",
            "z_N, мм",
            style,
            show_y_labels=True,
        )

        polyline: list[tuple[int, int]] = []
        for point in points:
            px = map_x(point.observation_index, left, right, x_range[0], x_range[1])
            py = map_y(point.z_mm, top, bottom, y_range[0], y_range[1])
            polyline.append((px, py))

        draw.line(polyline, fill=colors[cassette], width=max(2, scale))
        fit_start = (x_range[0], fit.slope_mm * x_range[0] + fit.intercept_mm)
        fit_end = (x_range[1], fit.slope_mm * x_range[1] + fit.intercept_mm)
        draw.line(
            (
                map_x(fit_start[0], left, right, x_range[0], x_range[1]),
                map_y(fit_start[1], top, bottom, y_range[0], y_range[1]),
                map_x(fit_end[0], left, right, x_range[0], x_range[1]),
                map_y(fit_end[1], top, bottom, y_range[0], y_range[1]),
            ),
            fill=style.line_color,
            width=max(1, scale),
        )

        radius = 5 * scale
        for point in points:
            px = map_x(point.observation_index, left, right, x_range[0], x_range[1])
            py = map_y(point.z_mm, top, bottom, y_range[0], y_range[1])
            err = abs(map_y(point.z_mm + point.z_error_mm, top, bottom, y_range[0], y_range[1]) - py)
            draw_errorbar(draw, px, py, err, colors[cassette], width=max(2, scale), cap=5 * scale)
            draw.ellipse(
                (px - radius, py - radius, px + radius, py + radius),
                fill=style.marker_fill,
                outline=colors[cassette],
                width=max(2, scale),
            )

    save_supersampled(image, size, ROOT / "all_self_reproduction_points.png")


def print_results() -> None:
    print("Спектральный метод")
    for point in SPECTRUM:
        print(
            f"{point.cassette}: d = {point.d_mm * 1000:.3f} ± {point.d_error_mm * 1000:.3f} um, "
            f"z_T = {point.talbot_mm:.3f} mm"
        )
    print("\nЛинзовый метод")
    for point in LENS:
        print(f"{point.cassette}: d = {point.d_mm * 1000:.3f} ± {point.d_error_mm * 1000:.3f} um")
    print("\nСаморепродукция")
    for cassette in ("K3", "K4", "K5"):
        fit = SELF_REP_FITS[cassette]
        print(
            f"{cassette}: z = ({fit.slope_mm:.3f} ± {fit.slope_error_mm:.3f}) N + "
            f"({fit.intercept_mm:.3f} ± {fit.intercept_error_mm:.3f}) mm; "
            f"R^2 = {fit.r_squared:.4f}; d = {fit.d_mm * 1000:.3f} ± {fit.d_error_mm * 1000:.3f} um"
        )


def main() -> None:
    make_all_self_rep_points_plot()
    print_results()


if __name__ == "__main__":
    main()
