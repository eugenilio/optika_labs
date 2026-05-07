#!/usr/bin/env python3

import csv
import json
import math
from pathlib import Path


LAB_DIR = Path("/home/eugenilio/optika/4.7.2")
DATA_PATH = LAB_DIR / "lab_data.csv"
RESULTS_PATH = LAB_DIR / "results.json"
PLOT_DATA_PATH = LAB_DIR / "rings_fit.dat"
PLOT_TEX_PATH = LAB_DIR / "rings_fit.tex"


def parse_sections(text: str) -> list[list[str]]:
    sections: list[list[str]] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                sections.append(current)
                current = []
            continue
        current.append(line)
    if current:
        sections.append(current)
    return sections


def parse_csv_block(lines: list[str]) -> list[dict[str, str]]:
    reader = csv.DictReader(lines, skipinitialspace=True)
    rows = []
    for row in reader:
        rows.append({(key or "").strip(): (value or "").strip() for key, value in row.items()})
    return rows


def weighted_mean(values: list[float], errors: list[float]) -> tuple[float, float]:
    weights = [1.0 / (err * err) for err in errors]
    mean = sum(v * w for v, w in zip(values, weights)) / sum(weights)
    err = math.sqrt(1.0 / sum(weights))
    return mean, err


def note_to_divisions(value: float) -> float:
    return value


def divisions_to_volts(value: float) -> float:
    return value * 15.0


def main() -> None:
    text = DATA_PATH.read_text(encoding="utf-8")
    sections = parse_sections(text)

    scalar_rows = {}
    for line in sections[0]:
        key, value = [part.strip() for part in line.split("=", 1)]
        scalar_rows[key] = value

    raw_L_cm = float(scalar_rows["L"].split()[0])
    raw_L_error_cm = float(scalar_rows["L_error"].split()[0])
    warnings = []

    if raw_L_cm > 100.0:
        L_cm = raw_L_cm / 10.0
        L_error_cm = raw_L_error_cm / 10.0
        warnings.append(
            "Raw data says L = 479 cm, but the textbook gives a working range of about 30-80 cm. "
            "For calculations L was interpreted as 479 mm = 47.9 cm."
        )
    else:
        L_cm = raw_L_cm
        L_error_cm = raw_L_error_cm

    ring_rows = parse_csv_block(sections[1])
    rings = []
    for row in ring_rows:
        m = int(row["ring_number"])
        diameter_cm = float(row["diameter_cm"])
        diameter_error_cm = float(row["diameter_error_cm"])
        radius_cm = diameter_cm / 2.0
        radius_error_cm = diameter_error_cm / 2.0
        radius_sq_cm2 = radius_cm * radius_cm
        radius_sq_error_cm2 = 2.0 * radius_cm * radius_error_cm
        rings.append(
            {
                "m": m,
                "diameter_cm": diameter_cm,
                "diameter_error_cm": diameter_error_cm,
                "radius_cm": radius_cm,
                "radius_error_cm": radius_error_cm,
                "radius_sq_cm2": radius_sq_cm2,
                "radius_sq_error_cm2": radius_sq_error_cm2,
            }
        )

    numerator = 0.0
    denominator = 0.0
    for row in rings:
        sigma = row["radius_sq_error_cm2"]
        weight = 1.0 / (sigma * sigma)
        numerator += weight * row["m"] * row["radius_sq_cm2"]
        denominator += weight * row["m"] * row["m"]
    slope_cm2 = numerator / denominator
    slope_error_cm2 = math.sqrt(1.0 / denominator)

    lambda_cm = 0.63e-4
    n_o = 2.29
    crystal_length_cm = 2.6
    crystal_width_cm = 0.3

    birefringence = lambda_cm * (n_o * L_cm) ** 2 / (crystal_length_cm * slope_cm2)
    birefringence_error = birefringence * math.sqrt(
        (slope_error_cm2 / slope_cm2) ** 2 + (2.0 * L_error_cm / L_cm) ** 2
    )

    dc_rows = parse_csv_block(sections[2])
    crossed_points = []
    parallel_points = []
    for row in dc_rows:
        if row["V_crossed"]:
            note_value = float(row["V_crossed"])
            note_error = float(row["V_crossed_error"])
            divisions = note_to_divisions(note_value)
            error_divisions = note_to_divisions(note_error)
            crossed_points.append(
                {
                    "label": row["point_type"],
                    "raw_note": note_value,
                    "raw_error_note": note_error,
                    "divisions": divisions,
                    "error_divisions": error_divisions,
                    "value": divisions_to_volts(divisions),
                    "error": divisions_to_volts(error_divisions),
                }
            )
        if row["V_parallel"]:
            note_value = float(row["V_parallel"])
            note_error = float(row["V_parallel_error"])
            divisions = note_to_divisions(note_value)
            error_divisions = note_to_divisions(note_error)
            parallel_points.append(
                {
                    "label": row["point_type"],
                    "raw_note": note_value,
                    "raw_error_note": note_error,
                    "divisions": divisions,
                    "error_divisions": error_divisions,
                    "value": divisions_to_volts(divisions),
                    "error": divisions_to_volts(error_divisions),
                }
            )

    dc_steps = []
    for series_name, series in [("crossed", crossed_points), ("parallel", parallel_points)]:
        for left, right in zip(series, series[1:]):
            dc_steps.append(
                {
                    "series": series_name,
                    "from": left["label"],
                    "to": right["label"],
                    "delta_v": right["value"] - left["value"],
                    "delta_error": math.sqrt(left["error"] ** 2 + right["error"] ** 2),
                }
            )

    dc_u_half, dc_u_half_error = weighted_mean(
        [item["delta_v"] for item in dc_steps],
        [item["delta_error"] for item in dc_steps],
    )

    quarter_parts = [part.strip() for part in sections[3][0].split(",")]
    quarter_note_raw = float(quarter_parts[1])
    quarter_note_raw_error = float(quarter_parts[2])
    quarter_note_div = note_to_divisions(quarter_note_raw)
    quarter_note_div_error = note_to_divisions(quarter_note_raw_error)
    quarter_note_v = divisions_to_volts(quarter_note_div)
    quarter_note_error_v = divisions_to_volts(quarter_note_div_error)
    quarter_theory_v = dc_u_half / 2.0
    quarter_theory_error_v = dc_u_half_error / 2.0
    warnings.append(
        f"The notebook entry for U_lambda/4 is {quarter_note_div:.1f} +- {quarter_note_div_error:.1f} divisions "
        f"({quarter_note_v:.0f} +- {quarter_note_error_v:.0f} V), "
        f"while the period of the intensity curve gives U_lambda/4 = {quarter_theory_v:.1f} +- "
        f"{quarter_theory_error_v:.1f} V. The U_lambda/4 note was treated as qualitative only."
    )

    osc_values = [part.strip() for part in sections[4][1].split(",")]
    ac_raw = float(osc_values[1])
    ac_raw_error = float(osc_values[2])
    ac_divisions = note_to_divisions(ac_raw)
    ac_error_divisions = note_to_divisions(ac_raw_error)
    ac_u_half = divisions_to_volts(ac_divisions)
    ac_u_half_error = divisions_to_volts(ac_error_divisions)

    delta_n_halfwave = 0.63e-6 / (4.0 * 26e-3)
    relative_delta_n = delta_n_halfwave / n_o

    results = {
        "constants": {
            "lambda_um": 0.63,
            "n_o": n_o,
            "crystal_length_cm": crystal_length_cm,
            "crystal_width_cm": crystal_width_cm,
        },
        "screen_distance": {
            "raw_value_cm": raw_L_cm,
            "raw_error_cm": raw_L_error_cm,
            "used_value_cm": L_cm,
            "used_error_cm": L_error_cm,
        },
        "rings": rings,
        "fit": {
            "slope_cm2": slope_cm2,
            "slope_error_cm2": slope_error_cm2,
        },
        "birefringence": {
            "value": birefringence,
            "error": birefringence_error,
        },
        "dc_steps": dc_steps,
        "u_half_dc": {
            "value_v": dc_u_half,
            "error_v": dc_u_half_error,
        },
        "u_half_ac": {
            "value_v": ac_u_half,
            "error_v": ac_u_half_error,
        },
        "u_quarter_theory": {
            "value_v": quarter_theory_v,
            "error_v": quarter_theory_error_v,
        },
        "u_quarter_note": {
            "raw_note": quarter_note_raw,
            "raw_error_note": quarter_note_raw_error,
            "divisions": quarter_note_div,
            "error_divisions": quarter_note_div_error,
            "value_v": quarter_note_v,
            "error_v": quarter_note_error_v,
        },
        "delta_n_halfwave": {
            "value": delta_n_halfwave,
            "relative_to_n_o": relative_delta_n,
        },
        "warnings": warnings,
    }

    RESULTS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["m y yerr"]
    for row in rings:
        lines.append(
            f"{row['m']} {row['radius_sq_cm2']:.6f} {row['radius_sq_error_cm2']:.6f}"
        )
    PLOT_DATA_PATH.write_text("\n".join(lines) + "\n", encoding="ascii")

    plot_tex = f"""\\documentclass[tikz,border=2pt]{{standalone}}
\\usepackage{{pgfplots}}
\\pgfplotsset{{compat=1.18}}

\\begin{{document}}
\\begin{{tikzpicture}}
\\begin{{axis}}[
    width=11cm,
    height=7cm,
    xlabel={{$m$}},
    ylabel={{$r^2$, cm$^2$}},
    xmin=0.5,
    xmax=5.5,
    ymin=0,
    ymax=45,
    grid=major,
    legend style={{draw=none, fill=none, at={{(0.03,0.97)}}, anchor=north west}},
]
\\addplot+[
    only marks,
    mark=*,
    mark size=2pt,
    black,
    error bars/.cd,
    y dir=both,
    y explicit,
] table[x=m, y=y, y error=yerr] {{{PLOT_DATA_PATH.name}}};
\\addlegendentry{{Data}}

\\addplot[
    domain=0:5.3,
    samples=2,
    thick,
    red,
] {{{slope_cm2:.6f}*x}};
\\addlegendentry{{$r^2 = ({slope_cm2:.2f}\\pm{slope_error_cm2:.2f})m$}}
\\end{{axis}}
\\end{{tikzpicture}}
\\end{{document}}
"""
    PLOT_TEX_PATH.write_text(plot_tex, encoding="utf-8")

    print(f"L used: {L_cm:.1f} ± {L_error_cm:.1f} cm")
    print(f"slope k = {slope_cm2:.3f} ± {slope_error_cm2:.3f} cm^2")
    print(f"n_o - n_e = {birefringence:.5f} ± {birefringence_error:.5f}")
    print(f"U_lambda/2 (DC) = {dc_u_half:.2f} ± {dc_u_half_error:.2f} V")
    print(f"U_lambda/2 (AC) = {ac_u_half:.2f} ± {ac_u_half_error:.2f} V")
    print(f"Expected U_lambda/4 from DC period = {quarter_theory_v:.2f} ± {quarter_theory_error_v:.2f} V")
    print(f"delta_n at U_lambda/2 = {delta_n_halfwave:.3e}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
