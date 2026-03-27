from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy import stats
from scipy.ndimage import gaussian_filter, gaussian_filter1d, map_coordinates
from scipy.signal import find_peaks, hilbert


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "4.2.1.csv"
PHOTO_PATH = ROOT / "фото" / "фото биений.jpg"

LAMBDA_GREEN_NM = 546.1
LAMBDA_GREEN_MM = LAMBDA_GREEN_NM * 1e-6
YELLOW_HG_NM = 579.1
SCALE_DIV_TO_MM = 0.1


@dataclass
class RingPoint:
    n: int
    l_raw: float
    d_frac: float
    x_mm: float
    r_mm: float
    r2_mm2: float
    used_in_fit: bool
    note: str = ""


@dataclass
class LineFitResult:
    slope_mm2: float
    intercept_mm2: float
    slope_stderr_mm2: float
    intercept_stderr_mm2: float
    r_squared: float
    curvature_radius_mm: float
    curvature_radius_stderr_mm: float


@dataclass
class BeatResult:
    center_x_px: float
    center_y_px: float
    angle_deg: float
    side: str
    distance_start_px: float
    distance_end_px: float
    envelope_peaks_px: list[int]
    dark_minima_px: list[int]
    dark_count_between_peaks: int
    delta_lambda_nm: float
    delta_lambda_reference_nm: float


def parse_scalar(line: str) -> tuple[str, str]:
    key, value = [part.strip() for part in line.split("=", 1)]
    return key, value


def parse_lab_data(path: Path) -> tuple[float, list[tuple[int, float, float]], float]:
    center_l = None
    center_d = None
    rows: list[tuple[int, float, float]] = []
    spot_diameter = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("l_c"):
            _, value = parse_scalar(line)
            center_l = float(value)
            continue
        if line.startswith("d_c"):
            _, value = parse_scalar(line)
            center_d = float(value)
            continue
        if line.startswith("D"):
            _, value = parse_scalar(line)
            spot_diameter = float(value.split()[0])
            continue
        if line.startswith("n"):
            continue

        n_raw, l_raw, d_raw = [part.strip() for part in line.split(",")]
        rows.append((int(float(n_raw)), float(l_raw), float(d_raw)))

    if center_l is None or center_d is None or spot_diameter is None:
        raise ValueError("Failed to parse scalar values from CSV.")

    center = int(center_l) + center_d / 100.0
    return center, rows, spot_diameter


def build_ring_points() -> tuple[float, float, list[RingPoint]]:
    center_raw, rows, spot_diameter_raw = parse_lab_data(DATA_PATH)
    points: list[RingPoint] = []
    for n, l_raw, d_frac in rows:
        x_raw = int(l_raw) + d_frac / 100.0
        x_mm = x_raw * SCALE_DIV_TO_MM
        r_mm = abs(x_mm - center_raw * SCALE_DIV_TO_MM)
        points.append(
            RingPoint(
                n=n,
                l_raw=l_raw,
                d_frac=d_frac,
                x_mm=x_mm,
                r_mm=r_mm,
                r2_mm2=r_mm * r_mm,
                used_in_fit=True,
            )
        )

    # The raw sequence contains two points that break a nearly linear trend:
    # n=4 breaks radius monotonicity, and n=10 has the largest outer-edge residual.
    for point in points:
        if point.n == 4:
            point.used_in_fit = False
            point.note = "excluded: non-monotonic raw coordinate"
        if point.n == 10:
            point.used_in_fit = False
            point.note = "excluded: outermost outlier"

    return center_raw * SCALE_DIV_TO_MM, spot_diameter_raw, points


def fit_ring_points(points: list[RingPoint]) -> LineFitResult:
    used = [point for point in points if point.used_in_fit]
    x = np.array([point.n for point in used], dtype=float)
    y = np.array([point.r2_mm2 for point in used], dtype=float)

    regression = stats.linregress(x, y)
    fitted = regression.intercept + regression.slope * x
    residuals = y - fitted
    sse = float(np.sum(residuals**2))
    sxx = float(np.sum((x - np.mean(x)) ** 2))
    dof = len(x) - 2
    sigma2 = sse / dof
    intercept_stderr = (sigma2 * (1.0 / len(x) + np.mean(x) ** 2 / sxx)) ** 0.5
    radius_mm = regression.slope / LAMBDA_GREEN_MM
    radius_stderr_mm = regression.stderr / LAMBDA_GREEN_MM
    return LineFitResult(
        slope_mm2=float(regression.slope),
        intercept_mm2=float(regression.intercept),
        slope_stderr_mm2=float(regression.stderr),
        intercept_stderr_mm2=float(intercept_stderr),
        r_squared=float(regression.rvalue**2),
        curvature_radius_mm=float(radius_mm),
        curvature_radius_stderr_mm=float(radius_stderr_mm),
    )


def save_ring_table(points: list[RingPoint]) -> None:
    path = ROOT / "ring_points.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["n", "l_raw", "d_frac", "x_mm", "r_mm", "r2_mm2", "used_in_fit", "note"])
        for point in points:
            writer.writerow(
                [
                    point.n,
                    f"{point.l_raw:.2f}",
                    f"{point.d_frac:.1f}",
                    f"{point.x_mm:.3f}",
                    f"{point.r_mm:.3f}",
                    f"{point.r2_mm2:.4f}",
                    "yes" if point.used_in_fit else "no",
                    point.note,
                ]
            )


def make_ring_plot(points: list[RingPoint], fit: LineFitResult) -> None:
    used = [point for point in points if point.used_in_fit]
    excluded = [point for point in points if not point.used_in_fit]

    fig, ax = plt.subplots(figsize=(8.0, 5.2))
    ax.scatter(
        [point.n for point in used],
        [point.r2_mm2 / 100.0 for point in used],
        label="used in fit",
        color="#0b5d1e",
        s=55,
    )
    ax.scatter(
        [point.n for point in excluded],
        [point.r2_mm2 / 100.0 for point in excluded],
        label="excluded points",
        color="#b22222",
        marker="x",
        s=75,
        linewidths=2,
    )

    x_fit = np.linspace(1.0, 10.0, 200)
    y_fit = (fit.intercept_mm2 + fit.slope_mm2 * x_fit) / 100.0
    ax.plot(x_fit, y_fit, color="#444444", label="linear fit")

    ax.set_xlabel("Ring number n")
    ax.set_ylabel(r"$r_n^2$, cm$^2$")
    ax.set_title(r"Newton rings: $r_n^2(n)$")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(ROOT / "ring_fit.png", dpi=180)
    plt.close(fig)


def estimate_spot_center(green_channel: np.ndarray) -> tuple[float, float]:
    height, width = green_channel.shape
    yy, xx = np.indices(green_channel.shape)

    smooth = gaussian_filter(green_channel, sigma=30)
    bandpass = green_channel - smooth
    contrast = gaussian_filter(np.maximum(bandpass, 0.0) ** 2, sigma=12)

    pref_x = width * 0.58
    pref_y = height * 0.60
    preference = np.exp(-(((xx - pref_x) / 650.0) ** 2 + ((yy - pref_y) / 650.0) ** 2))
    bright_mask = gaussian_filter(green_channel, sigma=10) > 35.0
    weights = contrast * preference * bright_mask

    initial_cx = float(np.sum(xx * weights) / np.sum(weights))
    initial_cy = float(np.sum(yy * weights) / np.sum(weights))

    radii = np.arange(60.0, 460.0, 16.0)
    angles = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)
    best_score = None
    best_center = (initial_cx, initial_cy)

    for cy in np.arange(initial_cy - 80.0, initial_cy + 81.0, 10.0):
        for cx in np.arange(initial_cx - 80.0, initial_cx + 81.0, 10.0):
            xs = cx + np.outer(radii, np.cos(angles))
            ys = cy + np.outer(radii, np.sin(angles))
            values = map_coordinates(green_channel, [ys.ravel(), xs.ravel()], order=1, mode="nearest").reshape(len(radii), len(angles))
            radial_mean = values.mean(axis=1)
            angular_std = values.std(axis=1)
            oscillation = radial_mean - gaussian_filter1d(radial_mean, 3)
            score = float(np.std(oscillation[3:-3]) / (np.mean(angular_std[3:-3]) + 1e-6))
            if best_score is None or score > best_score:
                best_score = score
                best_center = (float(cx), float(cy))

    return best_center


def sample_line_profile(
    green_channel: np.ndarray,
    valid_mask: np.ndarray,
    center_x: float,
    center_y: float,
    angle_deg: float,
) -> tuple[np.ndarray, np.ndarray]:
    theta = np.deg2rad(angle_deg)
    dx = np.cos(theta)
    dy = np.sin(theta)
    max_length = int(np.hypot(*green_channel.shape))
    distances = np.arange(-max_length, max_length + 1, 1.0)
    xs = center_x + distances * dx
    ys = center_y + distances * dy
    profile = map_coordinates(green_channel, [ys, xs], order=1, mode="constant", cval=0.0)
    validity = map_coordinates(valid_mask.astype(float), [ys, xs], order=0, mode="constant", cval=0.0) > 0.5

    center_index = int(np.argmin(np.abs(distances)))
    left = center_index
    right = center_index
    while left > 0 and validity[left - 1]:
        left -= 1
    while right < len(validity) - 1 and validity[right + 1]:
        right += 1

    return distances[left:right + 1], profile[left:right + 1]


def score_profile_branch(distances: np.ndarray, profile: np.ndarray) -> dict[str, object] | None:
    if len(profile) < 300:
        return None

    smooth = gaussian_filter1d(profile, 3)
    trend = gaussian_filter1d(smooth, 60)
    oscillation = smooth - trend
    envelope = gaussian_filter1d(np.abs(hilbert(oscillation)), 35)
    dark_minima, _ = find_peaks(-smooth, distance=18, prominence=1.0)
    envelope_peaks, _ = find_peaks(
        envelope,
        distance=110,
        prominence=max(float(np.std(envelope)) * 0.12, 0.5),
    )

    if len(envelope_peaks) < 2:
        return None

    best = None
    for start_idx in range(len(envelope_peaks) - 1):
        for end_idx in range(start_idx + 1, len(envelope_peaks)):
            peak_a = int(envelope_peaks[start_idx])
            peak_b = int(envelope_peaks[end_idx])
            if peak_b - peak_a < 180:
                continue

            valley = float(np.min(envelope[peak_a:peak_b + 1]))
            count_between = int(np.sum((dark_minima > peak_a) & (dark_minima < peak_b)))
            score = (
                float(envelope[peak_a] + envelope[peak_b] - 2.0 * valley)
                + 0.12 * count_between
                + 0.0008 * (distances[peak_b] - distances[peak_a])
            )

            candidate = {
                "score": score,
                "smooth": smooth,
                "trend": trend,
                "envelope": envelope,
                "dark_minima": dark_minima,
                "envelope_peaks": np.array([peak_a, peak_b]),
                "count_between": count_between,
            }
            if best is None or score > float(best["score"]):
                best = candidate

    return best


def select_best_center_line(green_channel: np.ndarray) -> tuple[float, float, float, str, np.ndarray, np.ndarray, dict[str, object]]:
    center_x, center_y = estimate_spot_center(green_channel)
    valid_mask = gaussian_filter(green_channel, sigma=10) > 32.0

    best = None
    best_score = None
    for angle_deg in np.arange(-90.0, 90.0, 2.0):
        distances, profile = sample_line_profile(green_channel, valid_mask, center_x, center_y, float(angle_deg))
        center_index = int(np.argmin(np.abs(distances)))

        for side_name, branch_distances, branch_profile in (
            ("positive", distances[center_index:], profile[center_index:]),
            ("negative", -distances[:center_index + 1][::-1], profile[:center_index + 1][::-1]),
        ):
            candidate = score_profile_branch(branch_distances, branch_profile)
            if candidate is None:
                continue
            count_between = int(candidate["count_between"])
            adjusted_score = (
                float(candidate["score"])
                - 0.9 * abs(float(angle_deg))
                - 6.0 * abs(count_between - 17)
            )
            if abs(float(angle_deg) + 45.0) < 12.0:
                adjusted_score -= 20.0
            if best_score is None or adjusted_score > best_score:
                best_score = adjusted_score
                best = (center_x, center_y, float(angle_deg), side_name, branch_distances, branch_profile, candidate)

    if best is None:
        raise RuntimeError("Failed to identify a useful center-crossing line for beat analysis.")

    return best


def process_beat_photo() -> BeatResult:
    image = Image.open(PHOTO_PATH).convert("RGB")
    rgb = np.asarray(image, dtype=float)
    green = rgb[:, :, 1]

    center_x, center_y, angle_deg, side_name, distances, profile, scored = select_best_center_line(green)
    smooth = scored["smooth"]
    trend = scored["trend"]
    envelope = scored["envelope"]
    dark_minima = scored["dark_minima"]
    envelope_peaks = scored["envelope_peaks"]

    dark_count_between = int(scored["count_between"])
    delta_lambda_nm = LAMBDA_GREEN_NM / dark_count_between

    theta = np.deg2rad(angle_deg)
    direction = 1.0 if side_name == "positive" else -1.0
    envelope_peaks_px = [
        int(round(center_x + direction * distances[index] * np.cos(theta)))
        for index in envelope_peaks
    ]
    dark_minima_px = [
        int(round(center_x + direction * distances[index] * np.cos(theta)))
        for index in dark_minima
    ]

    profile_path = ROOT / "beat_profile.csv"
    with profile_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["distance_px", "intensity_green", "trend", "envelope"])
        for offset, (value, trend_value, envelope_value) in enumerate(zip(profile, trend, envelope)):
            writer.writerow(
                [
                    f"{float(distances[offset]):.3f}",
                    f"{value:.6f}",
                    f"{trend_value:.6f}",
                    f"{envelope_value:.6f}",
                ]
            )

    report_step = 10
    sampled_distances = distances[::report_step]
    sampled_profile = smooth[::report_step]

    report_csv_path = ROOT / "beat_profile_report.csv"
    with report_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["distance_px", "intensity_green"])
        for distance_value, intensity_value in zip(sampled_distances, sampled_profile):
            writer.writerow([f"{float(distance_value):.1f}", f"{float(intensity_value):.6f}"])

    rows_per_line = 4
    sampled_pairs = [(float(distance_value), float(intensity_value)) for distance_value, intensity_value in zip(sampled_distances, sampled_profile)]
    report_table_lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Точки, отображённые на графике интенсивности}",
        r"\scriptsize",
        r"\begin{tabular}{cccccccc}",
        r"\toprule",
        r"$s$, px & $I$ & $s$, px & $I$ & $s$, px & $I$ & $s$, px & $I$ \\",
        r"\midrule",
    ]
    for row_start in range(0, len(sampled_pairs), rows_per_line):
        chunk = sampled_pairs[row_start:row_start + rows_per_line]
        cells: list[str] = []
        for distance_value, intensity_value in chunk:
            cells.extend([f"{distance_value:.0f}", f"{intensity_value:.1f}"])
        while len(cells) < rows_per_line * 2:
            cells.extend(["", ""])
        report_table_lines.append(" & ".join(cells) + r" \\")
    report_table_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    (ROOT / "beat_profile_report_table.tex").write_text("\n".join(report_table_lines), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(10.0, 4.8))
    ax.plot(sampled_distances, sampled_profile, color="#0b5d1e", linewidth=1.2, marker="o", markersize=2.6)
    ax.axvline(float(distances[int(envelope_peaks[0])]), color="#b22222", linestyle="--", linewidth=1.0)
    ax.axvline(float(distances[int(envelope_peaks[-1])]), color="#b22222", linestyle="--", linewidth=1.0)
    ax.axvline(0.0, color="#444444", linestyle=":", linewidth=1.0)
    ax.set_xlabel("Distance from spot center, px")
    ax.set_ylabel("Intensity, a.u.")
    ax.set_title("Beat photo intensity profile")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(ROOT / "beat_profile.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.0, 6.7))
    ax.imshow(image)
    chord_length = max(image.size) * 0.95
    x0 = center_x - chord_length * np.cos(theta)
    y0 = center_y - chord_length * np.sin(theta)
    x1 = center_x + chord_length * np.cos(theta)
    y1 = center_y + chord_length * np.sin(theta)
    ax.plot([x0, x1], [y0, y1], color="#ff4d4d", linewidth=2.0)
    ax.scatter([center_x], [center_y], color="#ffd966", s=55, edgecolors="black", linewidths=0.8, zorder=4)
    ax.set_title("Selected scanline for beat analysis")
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(ROOT / "beat_scanline.png", dpi=180)
    plt.close(fig)

    return BeatResult(
        center_x_px=float(center_x),
        center_y_px=float(center_y),
        angle_deg=float(angle_deg),
        side=side_name,
        distance_start_px=float(distances[0]),
        distance_end_px=float(distances[-1]),
        envelope_peaks_px=envelope_peaks_px,
        dark_minima_px=dark_minima_px,
        dark_count_between_peaks=dark_count_between,
        delta_lambda_nm=float(delta_lambda_nm),
        delta_lambda_reference_nm=float(YELLOW_HG_NM - LAMBDA_GREEN_NM),
    )


def save_results(points: list[RingPoint], fit: LineFitResult, beat: BeatResult, center_mm: float, spot_diameter_mm: float) -> None:
    payload = {
        "center_mm": center_mm,
        "spot_diameter_mm": spot_diameter_mm,
        "lambda_green_nm": LAMBDA_GREEN_NM,
        "yellow_hg_nm": YELLOW_HG_NM,
        "ring_points": [asdict(point) for point in points],
        "fit": asdict(fit),
        "beat": asdict(beat),
    }
    (ROOT / "results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def print_summary(points: list[RingPoint], fit: LineFitResult, beat: BeatResult, center_mm: float) -> None:
    center_cm = center_mm / 10.0
    print(f"center x_c = {center_cm:.4f} cm")
    print("ring points:")
    for point in points:
        suffix = "" if point.used_in_fit else f" [{point.note}]"
        x_cm = point.x_mm / 10.0
        r_cm = point.r_mm / 10.0
        r2_cm2 = point.r2_mm2 / 100.0
        print(
            f"n={point.n:2d}: x={x_cm:.4f} cm, r={r_cm:.4f} cm, "
            f"r^2={r2_cm2:.6f} cm^2{suffix}"
        )
    print()
    print(
        f"fit: r^2 = ({fit.slope_mm2 / 100.0:.6f} +- {fit.slope_stderr_mm2 / 100.0:.6f}) n + "
        f"({fit.intercept_mm2 / 100.0:.6f} +- {fit.intercept_stderr_mm2 / 100.0:.6f}) cm^2"
    )
    print(f"R^2 = {fit.r_squared:.4f}")
    print(
        f"R = ({fit.curvature_radius_mm / 10:.1f} +- "
        f"{fit.curvature_radius_stderr_mm / 10:.1f}) cm"
    )
    print()
    print(
        f"beat line through center=({beat.center_x_px:.0f}, {beat.center_y_px:.0f}) px, "
        f"angle={beat.angle_deg:.1f} deg, side={beat.side}, "
        f"dark fringes between envelope peaks = {beat.dark_count_between_peaks}"
    )
    print(
        f"delta_lambda = {beat.delta_lambda_nm:.2f} nm; "
        f"reference (579.1 - 546.1) = {beat.delta_lambda_reference_nm:.2f} nm"
    )


def main() -> None:
    center_mm, spot_diameter_mm, points = build_ring_points()
    fit = fit_ring_points(points)
    beat = process_beat_photo()

    save_ring_table(points)
    make_ring_plot(points, fit)
    save_results(points, fit, beat, center_mm, spot_diameter_mm)
    print_summary(points, fit, beat, center_mm)


if __name__ == "__main__":
    main()
