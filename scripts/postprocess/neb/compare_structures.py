#!/usr/bin/env python3
"""
compare_structures.py

Compare two structures using ASE.

Features
--------
- checks natoms, composition, and atom order
- compares cell parameters
- computes per-atom displacements
- computes RMSD and maximum displacement
- optional MIC (minimum image convention) for periodic structures
- optional rigid alignment (Kabsch) for non-periodic / ordered structures
- optional comparison of selected pair distances

Examples
--------
python3 compare_structures.py POSCAR CONTCAR
python3 compare_structures.py POSCAR CONTCAR --mic
python3 compare_structures.py POSCAR CONTCAR --align
python3 compare_structures.py POSCAR CONTCAR --pairs 1-2 1-5 7-9
python3 compare_structures.py POSCAR CONTCAR --mic --csv atom_displacements.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from ase.io import read
from ase.geometry import find_mic


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare two structures (cell, displacements, RMSD, selected bonds)."
    )
    parser.add_argument("structure1", help="First structure file")
    parser.add_argument("structure2", help="Second structure file")
    parser.add_argument(
        "--mic",
        action="store_true",
        help="Use minimum image convention for atom-by-atom displacements and pair distances.",
    )
    parser.add_argument(
        "--align",
        action="store_true",
        help="Apply rigid Kabsch alignment before computing displacements. "
             "Use only when atom order is identical and you want to remove rigid translation/rotation.",
    )
    parser.add_argument(
        "--pairs",
        nargs="*",
        default=[],
        help="Selected atom pairs to compare as 1-based indices, e.g. --pairs 1-2 1-5 7-9",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default="compare_structures_atoms.csv",
        help="Output CSV file for per-atom displacements (default: compare_structures_atoms.csv)",
    )
    parser.add_argument(
        "--summary",
        type=str,
        default="compare_structures_summary.txt",
        help="Output text summary file (default: compare_structures_summary.txt)",
    )
    return parser.parse_args()


def cell_params(cell):
    """Return (a, b, c, alpha, beta, gamma)."""
    return cell.cellpar()


def format_vec(v):
    return f"[{v[0]: .6f}, {v[1]: .6f}, {v[2]: .6f}]"


def parse_pairs(pair_strings, natoms):
    pairs = []
    for item in pair_strings:
        try:
            i_str, j_str = item.split("-")
            i = int(i_str)
            j = int(j_str)
        except Exception:
            raise ValueError(f"Invalid pair format '{item}'. Use 1-2 1-5 7-9 ...")

        if i < 1 or j < 1 or i > natoms or j > natoms:
            raise ValueError(f"Pair '{item}' out of range for natoms={natoms}")
        if i == j:
            raise ValueError(f"Pair '{item}' is invalid because both indices are equal")

        pairs.append((i - 1, j - 1))
    return pairs


def composition_dict(symbols):
    return dict(sorted(Counter(symbols).items(), key=lambda x: x[0]))


def composition_string(symbols):
    comp = composition_dict(symbols)
    return " ".join(f"{el}:{n}" for el, n in comp.items())


def symbols_same_order(sym1, sym2):
    return list(sym1) == list(sym2)


def kabsch_align(P, Q):
    """
    Align Q onto P using Kabsch.
    P and Q: (N,3)
    Returns aligned Q.
    """
    Pc = P - P.mean(axis=0)
    Qc = Q - Q.mean(axis=0)

    H = Qc.T @ Pc
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T

    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T

    Q_aligned = Qc @ R + P.mean(axis=0)
    return Q_aligned


def structures_have_compatible_cells(atoms1, atoms2, tol=1e-6):
    return np.allclose(atoms1.cell.array, atoms2.cell.array, atol=tol, rtol=0.0)


def compute_displacements(atoms1, atoms2, use_mic=False, align=False):
    pos1 = atoms1.get_positions().copy()
    pos2 = atoms2.get_positions().copy()

    if align:
        pos2 = kabsch_align(pos1, pos2)

    disp_vectors = []
    disp_norms = []

    if use_mic:
        if not structures_have_compatible_cells(atoms1, atoms2):
            raise ValueError(
                "MIC requested but the two cells are not identical within tolerance."
            )
        cell = atoms1.cell
        pbc = atoms1.pbc
        for r1, r2 in zip(pos1, pos2):
            dr = r2 - r1
            dr_mic, _ = find_mic(dr, cell, pbc=pbc)
            disp_vectors.append(dr_mic)
            disp_norms.append(np.linalg.norm(dr_mic))
    else:
        for r1, r2 in zip(pos1, pos2):
            dr = r2 - r1
            disp_vectors.append(dr)
            disp_norms.append(np.linalg.norm(dr))

    disp_vectors = np.array(disp_vectors)
    disp_norms = np.array(disp_norms)

    rmsd = float(np.sqrt(np.mean(disp_norms ** 2)))
    max_idx = int(np.argmax(disp_norms))
    max_disp = float(disp_norms[max_idx])

    return disp_vectors, disp_norms, rmsd, max_idx, max_disp


def compare_pairs(atoms1, atoms2, pairs, use_mic=False):
    results = []
    for i, j in pairs:
        d1 = atoms1.get_distance(i, j, mic=use_mic)
        d2 = atoms2.get_distance(i, j, mic=use_mic)
        results.append(
            {
                "pair": f"{i+1}-{j+1}",
                "distance1_A": d1,
                "distance2_A": d2,
                "delta_A": d2 - d1,
            }
        )
    return results


def write_csv(csv_path, atoms1, atoms2, disp_vectors, disp_norms):
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["index_1based", "symbol1", "symbol2", "dx_A", "dy_A", "dz_A", "disp_A"]
        )
        for i, (a1, a2, dv, dn) in enumerate(zip(atoms1, atoms2, disp_vectors, disp_norms), start=1):
            writer.writerow([i, a1.symbol, a2.symbol, dv[0], dv[1], dv[2], dn])


def build_summary_text(
    file1,
    file2,
    atoms1,
    atoms2,
    use_mic,
    align,
    disp_vectors,
    disp_norms,
    rmsd,
    max_idx,
    max_disp,
    pair_results,
):
    sym1 = atoms1.get_chemical_symbols()
    sym2 = atoms2.get_chemical_symbols()

    cp1 = cell_params(atoms1.cell)
    cp2 = cell_params(atoms2.cell)
    dcp = cp2 - cp1

    same_natoms = len(atoms1) == len(atoms2)
    same_comp = composition_dict(sym1) == composition_dict(sym2)
    same_order = symbols_same_order(sym1, sym2)

    lines = []
    lines.append("Structure comparison")
    lines.append("====================")
    lines.append("")
    lines.append(f"Structure 1: {file1}")
    lines.append(f"Structure 2: {file2}")
    lines.append("")
    lines.append("General checks")
    lines.append("--------------")
    lines.append(f"natoms structure 1: {len(atoms1)}")
    lines.append(f"natoms structure 2: {len(atoms2)}")
    lines.append(f"same natoms: {same_natoms}")
    lines.append(f"composition structure 1: {composition_string(sym1)}")
    lines.append(f"composition structure 2: {composition_string(sym2)}")
    lines.append(f"same composition: {same_comp}")
    lines.append(f"same atom order: {same_order}")
    lines.append(f"MIC used: {use_mic}")
    lines.append(f"Rigid alignment used: {align}")
    lines.append("")
    lines.append("Cell parameters")
    lines.append("---------------")
    labels = ["a", "b", "c", "alpha", "beta", "gamma"]
    units = ["A", "A", "A", "deg", "deg", "deg"]
    for lab, u, x1, x2, dx in zip(labels, units, cp1, cp2, dcp):
        lines.append(f"{lab:>5s}: {x1:12.6f} -> {x2:12.6f}   delta = {dx:+.6f} {u}")
    lines.append("")
    lines.append("Displacement statistics")
    lines.append("-----------------------")
    lines.append(f"RMSD: {rmsd:.6f} A")
    lines.append(f"Maximum displacement: {max_disp:.6f} A")
    lines.append(
        f"Atom with maximum displacement: index {max_idx+1} ({atoms1[max_idx].symbol} -> {atoms2[max_idx].symbol})"
    )
    lines.append(
        f"Displacement vector of max atom: {format_vec(disp_vectors[max_idx])} A"
    )
    lines.append("")
    lines.append("Per-atom displacements")
    lines.append("---------------------")
    lines.append(" idx   sym1  sym2      dx(A)        dy(A)        dz(A)       |dr|(A)")
    for i, (a1, a2, dv, dn) in enumerate(zip(atoms1, atoms2, disp_vectors, disp_norms), start=1):
        lines.append(
            f"{i:4d}   {a1.symbol:>3s}   {a2.symbol:>3s}   "
            f"{dv[0]:11.6f}  {dv[1]:11.6f}  {dv[2]:11.6f}  {dn:11.6f}"
        )

    if pair_results:
        lines.append("")
        lines.append("Selected pair distances")
        lines.append("-----------------------")
        lines.append(" pair      d1(A)        d2(A)       delta(A)")
        for row in pair_results:
            lines.append(
                f"{row['pair']:>6s}   {row['distance1_A']:11.6f}  "
                f"{row['distance2_A']:11.6f}  {row['delta_A']:11.6f}"
            )

    return "\n".join(lines) + "\n"


def main():
    args = parse_args()

    file1 = Path(args.structure1)
    file2 = Path(args.structure2)

    if not file1.is_file():
        print(f"ERROR: file not found: {file1}")
        sys.exit(1)
    if not file2.is_file():
        print(f"ERROR: file not found: {file2}")
        sys.exit(1)

    try:
        atoms1 = read(str(file1))
        atoms2 = read(str(file2))
    except Exception as exc:
        print(f"ERROR: failed to read structures with ASE: {exc}")
        sys.exit(1)

    if len(atoms1) != len(atoms2):
        print("ERROR: the two structures do not have the same number of atoms.")
        sys.exit(1)

    pairs = parse_pairs(args.pairs, len(atoms1)) if args.pairs else []

    sym1 = atoms1.get_chemical_symbols()
    sym2 = atoms2.get_chemical_symbols()

    if composition_dict(sym1) != composition_dict(sym2):
        print("WARNING: the two structures do not have the same composition.")

    if args.align and args.mic:
        print("ERROR: --align and --mic should not be used together in this version.")
        sys.exit(1)

    try:
        disp_vectors, disp_norms, rmsd, max_idx, max_disp = compute_displacements(
            atoms1, atoms2, use_mic=args.mic, align=args.align
        )
    except Exception as exc:
        print(f"ERROR: failed to compute displacements: {exc}")
        sys.exit(1)

    try:
        pair_results = compare_pairs(atoms1, atoms2, pairs, use_mic=args.mic) if pairs else []
    except Exception as exc:
        print(f"ERROR: failed to compare selected pairs: {exc}")
        sys.exit(1)

    summary_text = build_summary_text(
        file1=file1,
        file2=file2,
        atoms1=atoms1,
        atoms2=atoms2,
        use_mic=args.mic,
        align=args.align,
        disp_vectors=disp_vectors,
        disp_norms=disp_norms,
        rmsd=rmsd,
        max_idx=max_idx,
        max_disp=max_disp,
        pair_results=pair_results,
    )

    print(summary_text, end="")

    with open(args.summary, "w") as f:
        f.write(summary_text)

    write_csv(args.csv, atoms1, atoms2, disp_vectors, disp_norms)

    print(f"Summary written to: {args.summary}")
    print(f"Per-atom CSV written to: {args.csv}")


if __name__ == "__main__":
    main()