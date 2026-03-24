#!/usr/bin/env python3
from __future__ import annotations
import argparse
import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import matplotlib.pyplot as plt

from vasp_dos_tools import (
    read_total_dos,
    read_metadata,
    parse_atom_selection,
    read_projected_atoms,
    sum_selected_columns,
    integrate_window,
    band_center,
)


def crop_series(energies: List[float], values: List[float], emin: float | None, emax: float | None) -> Tuple[np.ndarray, np.ndarray]:
    e = np.asarray(energies, dtype=float)
    v = np.asarray(values, dtype=float)
    mask = np.ones_like(e, dtype=bool)
    if emin is not None:
        mask &= e >= emin
    if emax is not None:
        mask &= e <= emax
    return e[mask], v[mask]


def normalize_series(e: np.ndarray, v: np.ndarray, mode: str) -> np.ndarray:
    if mode == "none":
        return v.copy()
    if mode == "max":
        vmax = np.max(np.abs(v)) if v.size else 0.0
        return v / vmax if vmax > 0 else v.copy()
    if mode == "area":
        area = np.trapezoid(np.abs(v), e) if e.size > 1 else 0.0
        return v / area if area > 0 else v.copy()
    raise ValueError(f"Unknown normalization mode: {mode}")


def build_total_series(doscar: str) -> Tuple[List[float], Dict[str, List[float]]]:
    energies, labels, cols, _ = read_total_dos(doscar)
    series: Dict[str, List[float]] = {}
    if "dos" in labels:
        series["total"] = cols[labels.index("dos")]
    else:
        if "dos_up" in labels:
            series["total_up"] = cols[labels.index("dos_up")]
        if "dos_down" in labels:
            # Keep native positive sign for quantitative comparison.
            series["total_down"] = cols[labels.index("dos_down")]
        if "dos_up" in labels and "dos_down" in labels:
            up = np.asarray(cols[labels.index("dos_up")], dtype=float)
            down = np.asarray(cols[labels.index("dos_down")], dtype=float)
            series["total_sum"] = list(up + down)
    return energies, series


def build_projected_series(doscar: str, outcar: str, contcar: str, atoms_sel: str, orbitals: str | None) -> Tuple[List[float], Dict[str, List[float]], List[int]]:
    meta = read_metadata(doscar, outcar, contcar)
    atoms = parse_atom_selection(atoms_sel, meta)
    energies, labels, atom_data, _ = read_projected_atoms(atoms, doscar, outcar, contcar)
    orbital_list = [x.strip() for x in orbitals.split(",") if x.strip()] if orbitals else None
    series = sum_selected_columns(labels, atom_data, orbital_list)
    return energies, series, atoms


def prepare_series(args, which: str) -> Tuple[List[float], Dict[str, List[float]], str]:
    doscar = getattr(args, f"doscar_{which}")
    outcar = getattr(args, f"outcar_{which}")
    contcar = getattr(args, f"contcar_{which}")
    label = getattr(args, f"label_{which}")
    atoms = getattr(args, f"atoms_{which}") or args.atoms

    if atoms is None:
        energies, series = build_total_series(doscar)
        detail = "total DOS"
    else:
        energies, series, atom_list = build_projected_series(doscar, outcar, contcar, atoms, args.orbitals)
        detail = f"PDOS atoms={atom_list} orbitals={args.orbitals or 'default groups'}"
    return energies, series, detail if label is None else detail


def compare_on_common_grid(
    e1: np.ndarray,
    y1: np.ndarray,
    e2: np.ndarray,
    y2: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    left = max(float(np.min(e1)), float(np.min(e2)))
    right = min(float(np.max(e1)), float(np.max(e2)))
    if right <= left:
        return np.array([]), np.array([]), np.array([])

    ngrid = max(len(e1), len(e2), 400)
    grid = np.linspace(left, right, ngrid)
    y1i = np.interp(grid, e1, y1)
    y2i = np.interp(grid, e2, y2)
    return grid, y1i, y2i


def fmt(x: float) -> str:
    return "nan" if math.isnan(x) else f"{x:.6f}"


def main():
    ap = argparse.ArgumentParser(description="Automatically compare DOS/PDOS from two calculations.")
    ap.add_argument("--doscar-a", default="DOSCAR")
    ap.add_argument("--outcar-a", default="OUTCAR")
    ap.add_argument("--contcar-a", default="CONTCAR")
    ap.add_argument("--label-a", default="calc_A")
    ap.add_argument("--doscar-b", required=True)
    ap.add_argument("--outcar-b", default="OUTCAR")
    ap.add_argument("--contcar-b", default="CONTCAR")
    ap.add_argument("--label-b", default="calc_B")
    ap.add_argument("--atoms", default=None, help="Common atom selection for both calculations, e.g. 'Ni' or '1-8'. If omitted, compare total DOS.")
    ap.add_argument("--atoms-a", default=None, help="Atom selection only for calculation A.")
    ap.add_argument("--atoms-b", default=None, help="Atom selection only for calculation B.")
    ap.add_argument("--orbitals", default=None, help="Comma-separated orbital groups, e.g. 'd' or 'p,d' or 'dz2,dxz'. For PDOS mode.")
    ap.add_argument("--emin", type=float, default=None)
    ap.add_argument("--emax", type=float, default=None)
    ap.add_argument("--normalize", choices=["none", "max", "area"], default="none")
    ap.add_argument("--output-prefix", default="dos_compare")
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    energies_a, series_a, detail_a = prepare_series(args, "a")
    energies_b, series_b, detail_b = prepare_series(args, "b")

    common_keys = [k for k in series_a if k in series_b]
    if not common_keys:
        raise SystemExit(
            "No common DOS labels found between A and B. "
            f"A has: {', '.join(series_a.keys())}; B has: {', '.join(series_b.keys())}"
        )

    metrics_path = Path(f"{args.output_prefix}_metrics.txt")
    plot_path = Path(f"{args.output_prefix}.png")

    lines: List[str] = []
    lines.append(f"# A : {args.label_a}")
    lines.append(f"#    {detail_a}")
    lines.append(f"# B : {args.label_b}")
    lines.append(f"#    {detail_b}")
    lines.append(f"# normalize : {args.normalize}")
    lines.append(f"# window    : [{args.emin if args.emin is not None else '-inf'}, {args.emax if args.emax is not None else 'inf'}] eV relative to Ef")
    lines.append("# columns   : label area_A area_B center_A center_B delta_center overlap_L1 rms_diff")

    plt.figure(figsize=(8, 5))
    plotted = 0

    for key in common_keys:
        eA, yA = crop_series(energies_a, series_a[key], args.emin, args.emax)
        eB, yB = crop_series(energies_b, series_b[key], args.emin, args.emax)
        yA = normalize_series(eA, yA, args.normalize)
        yB = normalize_series(eB, yB, args.normalize)

        area_A = integrate_window(eA.tolist(), yA.tolist(), float(np.min(eA)), float(np.max(eA))) if eA.size >= 2 else float("nan")
        area_B = integrate_window(eB.tolist(), yB.tolist(), float(np.min(eB)), float(np.max(eB))) if eB.size >= 2 else float("nan")
        center_A = band_center(eA.tolist(), yA.tolist(), float(np.min(eA)), float(np.max(eA))) if eA.size >= 2 else float("nan")
        center_B = band_center(eB.tolist(), yB.tolist(), float(np.min(eB)), float(np.max(eB))) if eB.size >= 2 else float("nan")
        delta_center = center_B - center_A if (not math.isnan(center_A) and not math.isnan(center_B)) else float("nan")

        grid, yAi, yBi = compare_on_common_grid(eA, yA, eB, yB)
        if grid.size >= 2:
            overlap_L1 = np.trapezoid(np.abs(yAi - yBi), grid)
            rms_diff = float(np.sqrt(np.mean((yAi - yBi) ** 2)))
            dat = np.column_stack([grid, yAi, yBi, yBi - yAi])
            np.savetxt(f"{args.output_prefix}_{key}.dat", dat, header="E_minus_Ef A B B_minus_A")
        else:
            overlap_L1 = float("nan")
            rms_diff = float("nan")

        lines.append(
            f"{key:12s} {fmt(area_A):>14s} {fmt(area_B):>14s} {fmt(center_A):>14s} {fmt(center_B):>14s} {fmt(delta_center):>14s} {fmt(float(overlap_L1) if not np.isnan(overlap_L1) else float('nan')):>14s} {fmt(rms_diff):>14s}"
        )

        # Plot both calculations; mirror down channels to conventional negative representation.
        plotA = -yA if key.lower().endswith("down") else yA
        plotB = -yB if key.lower().endswith("down") else yB
        plt.plot(eA, plotA, label=f"{args.label_a}: {key}")
        plt.plot(eB, plotB, linestyle="--", label=f"{args.label_b}: {key}")
        plotted += 2

    metrics_path.write_text("\n".join(lines) + "\n")

    plt.axvline(0.0, linewidth=0.8)
    plt.axhline(0.0, linewidth=0.6)
    plt.xlabel(r"E - E$_F$ (eV)")
    plt.ylabel("DOS" if args.normalize == "none" else f"DOS ({args.normalize}-normalized)")
    if args.title:
        plt.title(args.title)
    if plotted <= 12:
        plt.legend(frameon=False, fontsize=8)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=200)

    print(f"Written {metrics_path}")
    print(f"Written {plot_path}")
    print("Compared labels:", ", ".join(common_keys))


if __name__ == "__main__":
    main()
