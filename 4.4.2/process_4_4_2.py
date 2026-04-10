#!/usr/bin/env python3
"""Process the field journal for MIPT lab 4.4.2.

The raw file is a handwritten journal, so the script keeps the parsing layer
explicit and writes a transparent inventory of accepted and rejected lines.

Notes:
- The first series in the journal is a real 22.5 deg series and is processed
  as such.
- The handbook text for this experiment describes 30 deg in the standard
  procedure, but the raw data in this workspace are not altered.
- Geometry is reconstructed using the journal convention: normal = 180 deg +
  psi, which is consistent with the zero-order readings.
- The file does not contain line-width measurements or grating passport values
  (m_p, lambda_p), so blaze-angle and resolution estimates are reported as
  unavailable instead of being invented.
"""

from __future__ import annotations

import csv
import functools
import json
import math
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Optional

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
RAW_PATH = ROOT / "4.4.2.csv"

OUT_DATA_INVENTORY = ROOT / "data_inventory.json"
OUT_PROCESSED_OBSERVATIONS = ROOT / "processed_observations.csv"
OUT_REJECTED_OBSERVATIONS = ROOT / "rejected_observations.csv"
OUT_FIRST_ORDER_POINTS = ROOT / "first_order_points.csv"
OUT_FIRST_ORDER_FIT = ROOT / "first_order_fit.csv"
OUT_YELLOW_DISPERSION = ROOT / "yellow_dispersion.csv"
OUT_PERIOD_ESTIMATES = ROOT / "period_estimates.csv"
OUT_PERIOD_SUMMARY = ROOT / "period_summary.csv"
OUT_SUMMARY = ROOT / "processing_bundle.json"
OUT_FIRST_ORDER_FIG = ROOT / "fig_first_order_fit.png"
OUT_YELLOW_FIG = ROOT / "fig_yellow_dispersion.png"
OUT_YELLOW_60_FIG = ROOT / "fig_yellow_dispersion_60deg.png"
OUT_PERIOD_FIG = ROOT / "fig_period_estimates.png"

COLLIMATOR_REFERENCE_DEG = 180.0
HG_WAVELENGTHS_NM = {
    "yellow1": 579.1,
    "yellow2": 577.0,
    "green": 546.1,
    "cyan": 491.6,
    "blue": 435.8,
    "violet": 404.7,
}


@dataclass
class RawRecord:
    raw_line: int
    block_deg: Optional[float]
    raw_text: str
    seq: Optional[int]
    reading_deg: Optional[float]
    comment: str
    color: Optional[str]
    status: str
    reason: str
    order: Optional[int] = None
    wavelength_nm: Optional[float] = None
    psi_deg: Optional[float] = None
    normal_deg: Optional[float] = None
    phi_deg: Optional[float] = None
    delta_sin: Optional[float] = None
    d_nm: Optional[float] = None


def parse_float_angle_from_header(line: str) -> Optional[float]:
    match = re.search(r"([0-9]+(?:[.,][0-9]+)?)", line)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def deg_min_to_deg(deg: float, minute: float) -> float:
    return deg + minute / 60.0


def normalize_text(text: str) -> str:
    return (
        text.lower()
        .replace("ё", "е")
        .replace("желый", "желтый")
        .replace("желая", "желтая")
        .replace("жетная", "желтая")
        .replace("жетлая", "желтая")
        .replace("филеотовая", "фиолетовая")
        .replace("фиалетовая", "фиолетовая")
        .replace("красня", "красная")
        .replace("голубой", "голубая")
        .replace("зеленый", "зеленая")
    )


def classify_color(comment: str) -> Optional[str]:
    text = normalize_text(comment)
    if "фиолет" in text:
        return "violet"
    if "голуб" in text:
        return "cyan"
    if "син" in text:
        return "blue"
    if "зелен" in text:
        return "green"
    if "желт" in text:
        return "yellow"
    if "бел" in text:
        return "white"
    if "крас" in text:
        return "red"
    return None


def parse_data_line(line: str) -> Optional[dict]:
    """Parse a raw measurement line."""

    stripped = line.strip()
    if not stripped:
        return None

    comment = ""
    if "#" in stripped:
        stripped, comment = stripped.split("#", 1)
        comment = comment.strip()

    match = re.match(r"^\s*(\d+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)\s*(.*)$", stripped)
    if not match:
        return None

    seq = int(match.group(1))
    deg = int(match.group(2))
    minute = int(match.group(3))
    tail = (match.group(4) or "").strip()
    tail = tail.lstrip(",").strip()
    if not comment:
        comment = tail
    elif tail:
        comment = f"{comment} {tail}".strip()

    return {
        "seq": seq,
        "deg": deg,
        "minute": minute,
        "reading_deg": deg_min_to_deg(deg, minute),
        "comment": comment,
    }


def through_origin_fit(xs: list[float], ys: list[float]) -> float:
    if not xs:
        raise ValueError("empty fit input")
    denom = math.fsum(v * v for v in xs)
    if denom == 0.0:
        raise ValueError("zero denominator in fit")
    return math.fsum(a * b for a, b in zip(xs, ys)) / denom


def rms(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    if not vals:
        return float("nan")
    return math.sqrt(math.fsum(v * v for v in vals) / len(vals))


def sample_std(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    if len(vals) < 2:
        return 0.0
    mean = math.fsum(vals) / len(vals)
    return math.sqrt(math.fsum((v - mean) ** 2 for v in vals) / (len(vals) - 1))


@functools.lru_cache(maxsize=None)
def _font(size: int = 16, bold: bool = False) -> ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            ]
        )
    candidates.extend(
        [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        ]
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fill: str = "black",
    size: int = 16,
    bold: bool = False,
) -> None:
    draw.text(xy, text, font=_font(size=size, bold=bold), fill=fill)


def _text_size(draw: ImageDraw.ImageDraw, text: str, size: int = 16, bold: bool = False) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=_font(size=size, bold=bold))
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _vertical_text(
    img: Image.Image,
    xy: tuple[int, int],
    text: str,
    fill: str = "black",
    size: int = 16,
    bold: bool = False,
) -> None:
    dummy = Image.new("RGBA", (1, 1), (255, 255, 255, 0))
    dummy_draw = ImageDraw.Draw(dummy)
    tw, th = _text_size(dummy_draw, text, size=size, bold=bold)
    label = Image.new("RGBA", (tw + 6, th + 6), (255, 255, 255, 0))
    label_draw = ImageDraw.Draw(label)
    label_draw.text((3, 3), text, font=_font(size=size, bold=bold), fill=fill)
    rotated = label.rotate(90, expand=True)
    img.paste(rotated, xy, rotated)


def _draw_axes(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    xlim: tuple[float, float],
    ylim: tuple[float, float],
    x_ticks: list[float],
    y_ticks: list[float],
    x_label: str,
    y_label: str,
    title: str,
) -> dict:
    left, top, right, bottom = box
    plot_left = left + 74
    plot_top = top + 28
    plot_right = right - 18
    plot_bottom = bottom - 44
    draw.rectangle([plot_left, plot_top, plot_right, plot_bottom], outline="black", width=1)

    x0, x1 = xlim
    y0, y1 = ylim

    def x_to_px(x: float) -> float:
        return plot_left + (x - x0) * (plot_right - plot_left) / (x1 - x0)

    def y_to_px(y: float) -> float:
        return plot_bottom - (y - y0) * (plot_bottom - plot_top) / (y1 - y0)

    for xt in x_ticks:
        px = x_to_px(xt)
        draw.line([(px, plot_bottom), (px, plot_bottom + 4)], fill="black")
        label = f"{xt:g}"
        tw, _ = _text_size(draw, label)
        _text(draw, (int(px - tw / 2), plot_bottom + 6), label)
        draw.line([(px, plot_top), (px, plot_bottom)], fill=(235, 235, 235))

    for yt in y_ticks:
        py = y_to_px(yt)
        draw.line([(plot_left - 4, py), (plot_left, py)], fill="black")
        label = f"{yt:.3f}" if abs(yt) < 1 else f"{yt:g}"
        tw, th = _text_size(draw, label)
        _text(draw, (plot_left - 10 - tw, int(py - th / 2)), label)
        draw.line([(plot_left, py), (plot_right, py)], fill=(235, 235, 235))

    xw, _ = _text_size(draw, x_label, size=18)
    tw, _ = _text_size(draw, title, size=19, bold=True)
    _text(draw, (int((plot_left + plot_right) / 2 - xw / 2), bottom - 28), x_label, size=18)
    _vertical_text(img, (left + 8, int((plot_top + plot_bottom) / 2 - 52)), y_label, size=18)
    _text(draw, (int((plot_left + plot_right) / 2 - tw / 2), top + 2), title, size=19, bold=True)

    return {
        "plot_left": plot_left,
        "plot_top": plot_top,
        "plot_right": plot_right,
        "plot_bottom": plot_bottom,
        "x_to_px": x_to_px,
        "y_to_px": y_to_px,
    }


def _scatter_point(draw: ImageDraw.ImageDraw, x: float, y: float, fill: str) -> None:
    r = 4
    draw.ellipse([x - r, y - r, x + r, y + r], outline="black", fill=fill, width=1)


def render_first_order_plot(first_order_by_block: dict[float, list[RawRecord]], block_fit_stats: dict[float, dict], path: Path) -> None:
    width, height = 1500, 520
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    panel_boxes = [
        (20, 20, 500, 480),
        (510, 20, 990, 480),
        (1000, 20, 1480, 480),
    ]
    block_colors = {22.5: "#2b6cb0", 45.0: "#c05621", 60.0: "#2f855a"}
    for box, block_deg in zip(panel_boxes, [22.5, 45.0, 60.0]):
        rows = first_order_by_block[block_deg]
        xs = [r.wavelength_nm for r in rows]
        ys = [r.delta_sin for r in rows]
        x_min = min(xs)
        x_max = max(xs)
        y_min = min(ys)
        y_max = max(ys)
        x_pad = 0.02 * (x_max - x_min if x_max > x_min else 1.0)
        y_pad = max(0.02, 0.15 * (y_max - y_min if y_max > y_min else max(abs(y_min), abs(y_max), 1e-3)))
        axes = _draw_axes(
            img,
            draw,
            box,
            (x_min - x_pad, x_max + x_pad),
            (y_min - y_pad, y_max + y_pad),
            [x_min, (x_min + x_max) / 2.0, x_max],
            [y_min, (y_min + y_max) / 2.0, y_max],
            "λ, нм",
            "sin φ - sin ψ",
            f"ψ = {block_deg:g}°",
        )
        slope = block_fit_stats[block_deg]["slope_per_nm"]
        xgrid = [x_min - x_pad, x_max + x_pad]
        color = block_colors[block_deg]
        x_to_px = axes["x_to_px"]
        y_to_px = axes["y_to_px"]
        draw.line(
            [(x_to_px(xgrid[0]), y_to_px(slope * xgrid[0])), (x_to_px(xgrid[1]), y_to_px(slope * xgrid[1]))],
            fill=color,
            width=2,
        )
        for x, y in zip(xs, ys):
            _scatter_point(draw, x_to_px(x), y_to_px(y), color)
        _text(draw, (box[0] + 92, box[1] + 34), f"d = {block_fit_stats[block_deg]['d_nm']:.1f} nm", size=17)
        _text(draw, (box[0] + 92, box[1] + 54), f"RMS = {block_fit_stats[block_deg]['rms_residual']:.2e}", size=17)
    _text(draw, (20, 0), "Аппроксимация", size=20, bold=True)
    img.save(path)


def render_yellow_plot(yellow_measurements: list[dict], path: Path) -> None:
    width, height = 950, 540
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    x_jitter = {22.5: -0.08, 45.0: 0.0, 60.0: 0.08}
    xs = [row["order"] + x_jitter[row["block_deg"]] for row in yellow_measurements]
    ys = [row["D_mrad_per_nm"] for row in yellow_measurements]
    x_min = 0.6
    x_max = 2.4
    y_min = min(ys)
    y_max = max(ys)
    y_pad = max(0.05, 0.15 * (y_max - y_min if y_max > y_min else max(abs(y_min), abs(y_max), 1e-3)))
    axes = _draw_axes(
        img,
        draw,
        (20, 20, 930, 470),
        (x_min, x_max),
        (y_min - y_pad, y_max + y_pad),
        [1.0, 1.5, 2.0],
        [y_min, (y_min + y_max) / 2.0, y_max],
        "Порядок m",
        "D, мрад/нм",
        "Угловая дисперсия жёлтого дублета",
    )
    colors = {22.5: "#2b6cb0", 45.0: "#c05621", 60.0: "#2f855a"}
    x_to_px = axes["x_to_px"]
    y_to_px = axes["y_to_px"]
    for row, x, y in zip(yellow_measurements, xs, ys):
        px, py = x_to_px(x), y_to_px(y)
        fill = colors[row["block_deg"]]
        if row["order"] == 1:
            draw.ellipse([px - 4, py - 4, px + 4, py + 4], outline="black", fill=fill, width=1)
        else:
            draw.rectangle([px - 4, py - 4, px + 4, py + 4], outline="black", fill=fill, width=1)

    legend_x = 650
    legend_y = 70
    _text(draw, (legend_x, legend_y - 18), "Серии", bold=True)
    for idx, block_deg in enumerate([22.5, 45.0, 60.0]):
        y = legend_y + idx * 22
        draw.rectangle([legend_x, y, legend_x + 10, y + 10], outline="black", fill=colors[block_deg], width=1)
        _text(draw, (legend_x + 16, y - 2), f"ψ = {block_deg:g}°")
    draw.ellipse([legend_x, legend_y + 72, legend_x + 8, legend_y + 80], outline="black", fill="gray", width=1)
    _text(draw, (legend_x + 16, legend_y + 68), "m = 1")
    draw.rectangle([legend_x, legend_y + 94, legend_x + 8, legend_y + 102], outline="black", fill="gray", width=1)
    _text(draw, (legend_x + 16, legend_y + 90), "m = 2")
    img.save(path)


def render_yellow_60_plot(yellow_measurements: list[dict], path: Path) -> None:
    rows = [row for row in yellow_measurements if row["block_deg"] == 60.0]
    if not rows:
        return

    width, height = 900, 560
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    xs = [float(row["order"]) for row in rows]
    exp_ys = [float(row["D_mrad_per_nm"]) for row in rows]
    th_ys = [float(row["D_theory_mrad_per_nm"]) for row in rows]
    y_min = min(exp_ys + th_ys)
    y_max = max(exp_ys + th_ys)
    y_pad = max(0.05, 0.18 * (y_max - y_min if y_max > y_min else 1.0))
    axes = _draw_axes(
        img,
        draw,
        (20, 20, 880, 500),
        (0.8, 3.2),
        (y_min - y_pad, y_max + y_pad),
        [1.0, 2.0, 3.0],
        [y_min, (y_min + y_max) / 2.0, y_max],
        "Порядок m",
        "D, мрад/нм",
        "Жёлтый дублет при ψ = 60°",
    )

    x_to_px = axes["x_to_px"]
    y_to_px = axes["y_to_px"]
    exp_points = [(x_to_px(x), y_to_px(y)) for x, y in zip(xs, exp_ys)]
    th_points = [(x_to_px(x), y_to_px(y)) for x, y in zip(xs, th_ys)]

    draw.line(exp_points, fill="#2f855a", width=2)
    draw.line(th_points, fill="#c05621", width=2)
    for px, py in exp_points:
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], outline="black", fill="#2f855a", width=1)
    for px, py in th_points:
        draw.rectangle([px - 4, py - 4, px + 4, py + 4], outline="black", fill="#c05621", width=1)

    legend_x = 625
    legend_y = 78
    _text(draw, (legend_x, legend_y - 22), "Обозначения", bold=True)
    draw.line([(legend_x, legend_y), (legend_x + 24, legend_y)], fill="#2f855a", width=2)
    draw.ellipse([legend_x + 8, legend_y - 4, legend_x + 16, legend_y + 4], outline="black", fill="#2f855a", width=1)
    _text(draw, (legend_x + 34, legend_y - 10), "эксперимент")
    draw.line([(legend_x, legend_y + 28), (legend_x + 24, legend_y + 28)], fill="#c05621", width=2)
    draw.rectangle([legend_x + 8, legend_y + 24, legend_x + 16, legend_y + 32], outline="black", fill="#c05621", width=1)
    _text(draw, (legend_x + 34, legend_y + 18), "теория")

    img.save(path)


def render_period_estimates_plot(period_estimates: list[dict], path: Path) -> None:
    width, height = 1200, 620
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    xs = [row["wavelength_nm"] for row in period_estimates if row["wavelength_nm"] is not None]
    ys = [row["d_nm"] for row in period_estimates if row["d_nm"] is not None]
    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)
    x_pad = 0.02 * (x_max - x_min if x_max > x_min else 1.0)
    y_pad = 0.05 * (y_max - y_min if y_max > y_min else max(abs(y_min), abs(y_max), 1e-3))
    axes = _draw_axes(
        img,
        draw,
        (20, 20, 1180, 570),
        (x_min - x_pad, x_max + x_pad),
        (y_min - y_pad, y_max + y_pad),
        [x_min, (x_min + x_max) / 2.0, x_max],
        [y_min, (y_min + y_max) / 2.0, y_max],
        "λ, нм",
        "d, нм",
        "Оценки периода по принятым наблюдениям",
    )

    colors = {22.5: "#2b6cb0", 45.0: "#c05621", 60.0: "#2f855a"}
    x_to_px = axes["x_to_px"]
    y_to_px = axes["y_to_px"]

    for row in period_estimates:
        x = row["wavelength_nm"]
        y = row["d_nm"]
        if x is None or y is None:
            continue
        px, py = x_to_px(x), y_to_px(y)
        fill = colors[row["block_deg"]]
        if row["order"] == 1:
            draw.ellipse([px - 4, py - 4, px + 4, py + 4], outline="black", fill=fill, width=1)
        elif row["order"] == 2:
            draw.rectangle([px - 4, py - 4, px + 4, py + 4], outline="black", fill=fill, width=1)
        else:
            draw.polygon([(px, py - 5), (px - 5, py + 4), (px + 5, py + 4)], outline="black", fill=fill)

    legend_x = 860
    legend_y = 70
    _text(draw, (legend_x, legend_y - 18), "Обозначения", bold=True)
    for idx, block_deg in enumerate([22.5, 45.0, 60.0]):
        y = legend_y + idx * 22
        draw.rectangle([legend_x, y, legend_x + 10, y + 10], outline="black", fill=colors[block_deg], width=1)
        _text(draw, (legend_x + 16, y - 2), f"ψ = {block_deg:g}°")
    draw.ellipse([legend_x, legend_y + 72, legend_x + 8, legend_y + 80], outline="black", fill="gray", width=1)
    _text(draw, (legend_x + 16, legend_y + 68), "m = 1")
    draw.rectangle([legend_x, legend_y + 94, legend_x + 8, legend_y + 102], outline="black", fill="gray", width=1)
    _text(draw, (legend_x + 16, legend_y + 90), "m = 2")
    draw.polygon(
        [(legend_x + 4, legend_y + 118), (legend_x - 1, legend_y + 127), (legend_x + 9, legend_y + 127)],
        outline="black",
        fill="gray",
    )
    _text(draw, (legend_x + 16, legend_y + 114), "m = 3")
    img.save(path)


def fit_uncertainty(xs: list[float], ys: list[float], slope: float) -> tuple[float, float]:
    if len(xs) < 2:
        return 0.0, 0.0
    residuals = [y - slope * x for x, y in zip(xs, ys)]
    s2 = math.fsum(res * res for res in residuals) / (len(xs) - 1)
    slope_se = math.sqrt(s2 / math.fsum(x * x for x in xs))
    d_se = slope_se / (slope * slope) if slope != 0 else 0.0
    return slope_se, d_se


def assign_classification(line_no: int, block_deg: float, parsed: dict) -> tuple[str, str, Optional[int], Optional[float]]:
    """Manual but explicit classification of the field journal."""

    comment = parsed["comment"]
    color = classify_color(comment)

    accepted_zero = {3, 18, 40}
    accepted_m1 = {
        4, 5, 6, 7, 8, 9, 10,
        19, 20, 21, 22, 23, 24,
        41, 42, 43, 44, 45, 46,
    }
    accepted_m2 = {13, 30, 31, 32, 33, 34, 35, 53, 54}
    accepted_m3 = {56, 57}
    rejected_incomplete = {14, 63}
    rejected_ambiguous = {11, 25, 26, 27, 36, 48, 49, 50, 51, 52, 62}

    if line_no in accepted_zero:
        return "accepted", "reference white zero order", 0, None
    if line_no in accepted_m1:
        if color == "yellow":
            return "accepted", "first-order Hg line", 1, None
        if color in HG_WAVELENGTHS_NM:
            return "accepted", "first-order Hg line", 1, HG_WAVELENGTHS_NM[color]
        return "rejected", "first-order note does not match a visible Hg line", None, None
    if line_no in accepted_m2:
        if color in HG_WAVELENGTHS_NM or color == "yellow":
            return "accepted", "second-order Hg line", 2, None
        return "rejected", "second-order note does not match a visible Hg line", None, None
    if line_no in accepted_m3:
        if color in HG_WAVELENGTHS_NM or color == "yellow":
            return "accepted", "third-order Hg line", 3, None
        return "rejected", "third-order note does not match a visible Hg line", None, None
    if line_no in rejected_incomplete:
        return "rejected", "incomplete entry", None, None
    if line_no in rejected_ambiguous:
        return "rejected", "ambiguous or non-Hg note", None, None
    return "skipped", "header/comment/blank", None, None


def main() -> None:
    raw_lines = RAW_PATH.read_text(encoding="utf-8").splitlines()
    raw_records: list[RawRecord] = []
    skipped_context: list[dict] = []
    current_block: Optional[float] = None

    for line_no, line in enumerate(raw_lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("для "):
            current_block = parse_float_angle_from_header(stripped)
            skipped_context.append(
                {"raw_line": line_no, "kind": "header", "text": stripped, "block_deg": current_block}
            )
            continue
        if not re.match(r"^\d+\s*,", stripped):
            skipped_context.append(
                {"raw_line": line_no, "kind": "comment", "text": stripped, "block_deg": current_block}
            )
            continue

        parsed = parse_data_line(stripped)
        if parsed is None:
            raw_records.append(
                RawRecord(
                    raw_line=line_no,
                    block_deg=current_block,
                    raw_text=stripped,
                    seq=None,
                    reading_deg=None,
                    comment="",
                    color=None,
                    status="rejected",
                    reason="unparsed data line",
                )
            )
            continue

        status, reason, order, wavelength_nm = assign_classification(line_no, current_block or float("nan"), parsed)
        color = classify_color(parsed["comment"])
        raw_records.append(
            RawRecord(
                raw_line=line_no,
                block_deg=current_block,
                raw_text=stripped,
                seq=parsed["seq"],
                reading_deg=parsed["reading_deg"],
                comment=parsed["comment"],
                color=color,
                status=status,
                reason=reason,
                order=order,
                wavelength_nm=wavelength_nm,
            )
        )

    accepted = [r for r in raw_records if r.status == "accepted"]
    rejected = [r for r in raw_records if r.status == "rejected"]
    line_by_no = {r.raw_line: r for r in accepted}

    # Geometry reconstruction.
    for rec in accepted:
        if rec.block_deg is None:
            continue
        rec.psi_deg = float(rec.block_deg)
        rec.normal_deg = COLLIMATOR_REFERENCE_DEG + rec.psi_deg
        if rec.reading_deg is None:
            continue
        rec.phi_deg = abs(rec.reading_deg - rec.normal_deg)
        rec.delta_sin = math.sin(math.radians(rec.phi_deg)) - math.sin(math.radians(rec.psi_deg))

    # Correct the yellow doublet labels by angle ordering.
    yellow_assignments = {
        9: "yellow2",
        10: "yellow1",
        23: "yellow1",
        24: "yellow2",
        34: "yellow2",
        35: "yellow1",
        45: "yellow1",
        46: "yellow2",
        53: "yellow1",
        54: "yellow2",
        56: "yellow2",
        57: "yellow1",
    }
    for line_no, color in yellow_assignments.items():
        rec = line_by_no[line_no]
        rec.color = color
        rec.wavelength_nm = HG_WAVELENGTHS_NM[color]

    if 13 in line_by_no:
        line_by_no[13].color = "violet"
        line_by_no[13].wavelength_nm = HG_WAVELENGTHS_NM["violet"]

    for rec in accepted:
        if rec.wavelength_nm is None and rec.color in HG_WAVELENGTHS_NM:
            rec.wavelength_nm = HG_WAVELENGTHS_NM[rec.color]
        if rec.order and rec.wavelength_nm is not None and rec.delta_sin is not None and abs(rec.delta_sin) > 1e-12:
            rec.d_nm = rec.order * rec.wavelength_nm / abs(rec.delta_sin)

    accepted_rows = [asdict(r) for r in accepted]
    rejected_rows = [asdict(r) for r in rejected]

    # First-order fits by block.
    first_order_by_block: dict[float, list[RawRecord]] = {22.5: [], 45.0: [], 60.0: []}
    for rec in accepted:
        if rec.order == 1 and rec.wavelength_nm is not None and rec.delta_sin is not None:
            first_order_by_block[float(rec.block_deg)].append(rec)

    first_order_fit_rows: list[dict] = []
    block_fit_stats: dict[float, dict] = {}
    for block_deg, rows in first_order_by_block.items():
        xs = [float(r.wavelength_nm) for r in rows]
        ys = [float(r.delta_sin) for r in rows]
        slope = through_origin_fit(xs, ys)
        d_nm = abs(1.0 / slope)
        slope_se, d_se = fit_uncertainty(xs, ys, slope)
        fitted = [slope * x for x in xs]
        residuals = [y - fy for y, fy in zip(ys, fitted)]
        block_fit_stats[block_deg] = {
            "slope_per_nm": slope,
            "slope_se_per_nm": slope_se,
            "d_nm": d_nm,
            "d_se_nm": d_se,
            "n_points": len(xs),
            "rms_residual": rms(residuals),
        }
        for row, x, y, yfit, res in zip(rows, xs, ys, fitted, residuals):
            first_order_fit_rows.append(
                {
                    "block_deg": block_deg,
                    "wavelength_nm": x,
                    "delta_sin": y,
                    "delta_fit": yfit,
                    "residual": res,
                    "order": row.order,
                }
            )

    combined_first_order_x = [float(r.wavelength_nm) for r in accepted if r.order == 1 and r.wavelength_nm is not None and r.delta_sin is not None]
    combined_first_order_y = [abs(float(r.delta_sin)) for r in accepted if r.order == 1 and r.wavelength_nm is not None and r.delta_sin is not None]
    combined_first_order_slope = through_origin_fit(combined_first_order_x, combined_first_order_y)
    combined_d_nm = 1.0 / combined_first_order_slope
    combined_slope_se, combined_d_se = fit_uncertainty(combined_first_order_x, combined_first_order_y, combined_first_order_slope)

    # Yellow doublet dispersion.
    yellow_pairs = [
        {"block_deg": 22.5, "order": 1, "line_nos": (9, 10)},
        {"block_deg": 45.0, "order": 1, "line_nos": (23, 24)},
        {"block_deg": 45.0, "order": 2, "line_nos": (34, 35)},
        {"block_deg": 60.0, "order": 1, "line_nos": (45, 46)},
        {"block_deg": 60.0, "order": 2, "line_nos": (53, 54)},
        {"block_deg": 60.0, "order": 3, "line_nos": (56, 57)},
    ]
    yellow_measurements: list[dict] = []
    delta_lambda_nm = abs(HG_WAVELENGTHS_NM["yellow1"] - HG_WAVELENGTHS_NM["yellow2"])
    for pair in yellow_pairs:
        r1 = line_by_no[pair["line_nos"][0]]
        r2 = line_by_no[pair["line_nos"][1]]
        phi1 = float(r1.phi_deg)
        phi2 = float(r2.phi_deg)
        delta_phi_deg = abs(phi1 - phi2)
        delta_phi_rad = math.radians(delta_phi_deg)
        D_deg_per_nm = delta_phi_deg / delta_lambda_nm
        D_rad_per_nm = delta_phi_rad / delta_lambda_nm
        phi_mean_rad = math.radians((phi1 + phi2) / 2.0)
        D_theory_rad_per_nm = pair["order"] / (combined_d_nm * math.cos(phi_mean_rad))
        yellow_measurements.append(
            {
                "block_deg": pair["block_deg"],
                "order": pair["order"],
                "line_no_1": pair["line_nos"][0],
                "line_no_2": pair["line_nos"][1],
                "phi1_deg": phi1,
                "phi2_deg": phi2,
                "delta_phi_deg": delta_phi_deg,
                "delta_phi_rad": delta_phi_rad,
                "delta_lambda_nm": delta_lambda_nm,
                "D_deg_per_nm": D_deg_per_nm,
                "D_rad_per_nm": D_rad_per_nm,
                "D_mrad_per_nm": D_rad_per_nm * 1000.0,
                "D_theory_rad_per_nm": D_theory_rad_per_nm,
                "D_theory_mrad_per_nm": D_theory_rad_per_nm * 1000.0,
            }
        )

    period_estimates: list[dict] = []
    for rec in accepted:
        if rec.order is None or rec.order == 0 or rec.wavelength_nm is None or rec.d_nm is None:
            continue
        period_estimates.append(
            {
                "raw_line": rec.raw_line,
                "block_deg": rec.block_deg,
                "seq": rec.seq,
                "order": rec.order,
                "color": rec.color,
                "wavelength_nm": rec.wavelength_nm,
                "delta_sin": rec.delta_sin,
                "d_nm": rec.d_nm,
                "phi_deg": rec.phi_deg,
                "reading_deg": rec.reading_deg,
            }
        )

    period_summary_rows: list[dict] = []
    for block_deg in [22.5, 45.0, 60.0]:
        for order in [1, 2, 3]:
            block_order_rows = [
                row for row in period_estimates if row["block_deg"] == block_deg and row["order"] == order
            ]
            if not block_order_rows:
                continue
            d_vals = [float(row["d_nm"]) for row in block_order_rows]
            period_summary_rows.append(
                {
                    "group_kind": "block_order",
                    "block_deg": block_deg,
                    "order": order,
                    "group_value": f"{block_deg:g}/{order}",
                    "n_points": len(d_vals),
                    "mean_d_nm": math.fsum(d_vals) / len(d_vals),
                    "std_d_nm": sample_std(d_vals),
                    "min_d_nm": min(d_vals),
                    "max_d_nm": max(d_vals),
                }
            )
    for order in [1, 2, 3]:
        order_rows = [row for row in period_estimates if row["order"] == order]
        d_vals = [float(row["d_nm"]) for row in order_rows]
        period_summary_rows.append(
            {
                "group_kind": "order",
                "block_deg": "",
                "group_value": order,
                "order": order,
                "n_points": len(d_vals),
                "mean_d_nm": math.fsum(d_vals) / len(d_vals),
                "std_d_nm": sample_std(d_vals),
                "min_d_nm": min(d_vals),
                "max_d_nm": max(d_vals),
            }
        )
    first_order_rows = [row for row in period_estimates if row["order"] == 1]
    first_order_d_vals = [float(row["d_nm"]) for row in first_order_rows]
    period_summary_rows.append(
        {
            "group_kind": "combined_first_order",
            "block_deg": "",
            "group_value": "all",
            "order": 1,
            "n_points": len(first_order_d_vals),
            "mean_d_nm": math.fsum(first_order_d_vals) / len(first_order_d_vals),
            "std_d_nm": sample_std(first_order_d_vals),
            "min_d_nm": min(first_order_d_vals),
            "max_d_nm": max(first_order_d_vals),
        }
    )

    # Write CSV tables.
    with OUT_PROCESSED_OBSERVATIONS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(accepted_rows[0].keys()))
        writer.writeheader()
        writer.writerows(accepted_rows)

    with OUT_REJECTED_OBSERVATIONS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rejected_rows[0].keys()) if rejected_rows else ["raw_line"])
        writer.writeheader()
        if rejected_rows:
            writer.writerows(rejected_rows)

    with OUT_FIRST_ORDER_POINTS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["block_deg", "wavelength_nm", "delta_sin", "order"])
        writer.writeheader()
        for row in first_order_fit_rows:
            writer.writerow(
                {
                    "block_deg": row["block_deg"],
                    "wavelength_nm": row["wavelength_nm"],
                    "delta_sin": row["delta_sin"],
                    "order": row["order"],
                }
            )

    with OUT_FIRST_ORDER_FIT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["block_deg", "wavelength_nm", "delta_sin", "delta_fit", "residual", "order"])
        writer.writeheader()
        writer.writerows(first_order_fit_rows)

    with OUT_YELLOW_DISPERSION.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(yellow_measurements[0].keys()))
        writer.writeheader()
        writer.writerows(yellow_measurements)

    with OUT_PERIOD_ESTIMATES.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["raw_line", "block_deg", "seq", "order", "color", "wavelength_nm", "delta_sin", "d_nm", "phi_deg", "reading_deg"],
        )
        writer.writeheader()
        writer.writerows(period_estimates)

    with OUT_PERIOD_SUMMARY.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["group_kind", "block_deg", "order", "group_value", "n_points", "mean_d_nm", "std_d_nm", "min_d_nm", "max_d_nm"],
        )
        writer.writeheader()
        writer.writerows(period_summary_rows)

    all_rows = sorted(accepted_rows + rejected_rows, key=lambda r: r["raw_line"])

    data_inventory = {
        "source_file": str(RAW_PATH),
        "notes": [
            "The first series in the journal is a real 22.5 deg series and is processed as such.",
            "The handbook text for work 4.4.2 describes 30 deg in the standard procedure, but the raw data in this workspace are not altered.",
            "Geometry is reconstructed using the journal convention: normal = 180 deg + psi, verified by the zero-order readings.",
            "Yellow-doublet labels in the handwritten notes are corrected by angle ordering; the longer wavelength is assigned to the larger diffraction angle.",
            "Per-observation period estimates and group summaries are generated from the accepted rows to provide a consistency check across blocks and orders.",
        ],
        "counts": {
            "accepted": len(accepted_rows),
            "rejected": len(rejected_rows),
            "skipped_context": len(skipped_context),
        },
        "rows": all_rows,
        "skipped_context": skipped_context,
    }

    processing_bundle = {
        "source_file": str(RAW_PATH),
        "flags": {
            "first_series_deg": 22.5,
            "methodology_series_deg_in_handbook": 30.0,
            "angle_mismatch_note": "The journal uses 22.5 deg for the first series; the handbook text for this work discusses 30 deg. The raw data were not converted.",
            "missing_inputs": [
                "No grating passport values m_p and lambda_p are present in the raw file, so the blaze angle cannot be computed from (4.5) without inventing data.",
                "No line-width / zero-intensity width measurements are present in the raw file, so delta-lambda, resolving power and effective number of working grooves cannot be completed from this dataset alone.",
            ],
            "new_report_facing_outputs": [
                OUT_PERIOD_ESTIMATES.name,
                OUT_PERIOD_SUMMARY.name,
                OUT_PERIOD_FIG.name,
                OUT_YELLOW_60_FIG.name,
            ],
        },
        "grating_period_fit": {
            "combined_first_order_slope_per_nm": combined_first_order_slope,
            "combined_first_order_slope_se_per_nm": combined_slope_se,
            "combined_d_nm": combined_d_nm,
            "combined_d_se_nm": combined_d_se,
            "block_fits": block_fit_stats,
        },
        "period_consistency": {
            "period_estimates_file": OUT_PERIOD_ESTIMATES.name,
            "period_summary_file": OUT_PERIOD_SUMMARY.name,
            "plot_file": OUT_PERIOD_FIG.name,
            "summary_rows": period_summary_rows,
        },
        "yellow_dispersion": yellow_measurements,
        "observations": {
            "accepted": accepted_rows,
            "rejected": rejected_rows,
        },
    }

    # Render plots without relying on matplotlib.
    render_first_order_plot(first_order_by_block, block_fit_stats, OUT_FIRST_ORDER_FIG)
    render_yellow_plot(yellow_measurements, OUT_YELLOW_FIG)
    render_yellow_60_plot(yellow_measurements, OUT_YELLOW_60_FIG)
    render_period_estimates_plot(period_estimates, OUT_PERIOD_FIG)

    generated_files = [
        OUT_PROCESSED_OBSERVATIONS.name,
        OUT_REJECTED_OBSERVATIONS.name,
        OUT_FIRST_ORDER_POINTS.name,
        OUT_FIRST_ORDER_FIT.name,
        OUT_YELLOW_DISPERSION.name,
        OUT_FIRST_ORDER_FIG.name,
        OUT_YELLOW_FIG.name,
        OUT_YELLOW_60_FIG.name,
        OUT_PERIOD_ESTIMATES.name,
        OUT_PERIOD_SUMMARY.name,
        OUT_PERIOD_FIG.name,
        OUT_DATA_INVENTORY.name,
        OUT_SUMMARY.name,
    ]
    data_inventory["generated_files"] = generated_files
    processing_bundle["generated_files"] = generated_files

    with OUT_DATA_INVENTORY.open("w", encoding="utf-8") as f:
        json.dump(data_inventory, f, ensure_ascii=False, indent=2)

    with OUT_SUMMARY.open("w", encoding="utf-8") as f:
        json.dump(processing_bundle, f, ensure_ascii=False, indent=2)

    print("Generated:")
    for name in generated_files:
        print(name)


if __name__ == "__main__":
    main()
