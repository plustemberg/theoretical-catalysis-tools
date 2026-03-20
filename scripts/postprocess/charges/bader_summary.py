#!/usr/bin/env python3
"""
bader_summary.py

Summarize Bader charges from ACF.dat and a structure file (POSCAR/CONTCAR/etc.).

Features
--------
- reads ACF.dat produced by the Henkelman Bader code
- reads atomic symbols and positions from a structure file using ASE
- reports Bader electrons per atom
- computes approximate net charge if reference valence electrons are provided
- supports user-defined groups of atoms
- writes text and CSV summaries

Examples
--------
python3 bader_summary.py --acf ACF.dat --structure CONTCAR
python3 bader_summary.py --acf ACF.dat --structure CONTCAR --ref Ce=12 O=6 Ni=10 C=4 H=1
python3 bader_summary.py --acf ACF.dat --structure CONTCAR --groups Ni_cluster:1-6 support:7-120 ads:121-126
python3 bader_summary.py --acf ACF.dat --structure CONTCAR --ref Ce=12 O=6 Ni=10 --groups cluster:1-8 slab:9-120
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

from ase.io import read


def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize Bader charges from ACF.dat and a structure file."
    )
    parser.add_argument("--acf", required=True, help="Path to ACF.dat")
    parser.add_argument(
        "--structure",
        required=True,
        help="Structure file readable by ASE (e.g. POSCAR, CONTCAR, .xyz)",
    )
    parser.add_argument(
        "--ref",
        nargs="*",
        default=[],
        help="Reference valence electrons by element, e.g. Ce=12 O=6 Ni=10 C=4 H=1",
    )
    parser.add_argument(
        "--groups",
        nargs="*",
        default=[],
        help=(
            "Atom groups using 1-based indices, e.g. "
            "cluster:1-6 support:7-120 ads:121-126"
        ),
    )
    parser.add_argument(
        "--atoms-csv",
        default="bader_atoms.csv",
        help="Output CSV with atom-by-atom data (default: bader_atoms.csv)",
    )
    parser.add_argument(
        "--groups-csv",
        default="bader_groups.csv",
        help="Output CSV with group data (default: bader_groups.csv)",
    )
    parser.add_argument(
        "--summary",
        default="bader_summary.txt",
        help="Output text summary (default: bader_summary.txt)",
    )
    return parser.parse_args()


def parse_ref_list(ref_items):
    refs = {}
    for item in ref_items:
        if "=" not in item:
            raise ValueError(f"Invalid reference entry '{item}'. Use Element=value, e.g. O=6")
        el, val = item.split("=", 1)
        el = el.strip()
        if not re.fullmatch(r"[A-Z][a-z]?", el):
            raise ValueError(f"Invalid element symbol in '{item}'")
        refs[el] = float(val)
    return refs


def parse_index_spec(spec, natoms):
    """
    Parse strings like:
    - 1-6
    - 1,2,4,8
    - 1-6,10,15-18
    Returns sorted unique 0-based indices.
    """
    indices = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a_str, b_str = chunk.split("-", 1)
            a = int(a_str)
            b = int(b_str)
            if a > b:
                raise ValueError(f"Invalid range '{chunk}'")
            for i in range(a, b + 1):
                if i < 1 or i > natoms:
                    raise ValueError(f"Index {i} out of range for natoms={natoms}")
                indices.add(i - 1)
        else:
            i = int(chunk)
            if i < 1 or i > natoms:
                raise ValueError(f"Index {i} out of range for natoms={natoms}")
            indices.add(i - 1)
    return sorted(indices)


def parse_groups(group_items, natoms):
    groups = []
    for item in group_items:
        if ":" not in item:
            raise ValueError(
                f"Invalid group entry '{item}'. Use name:1-6 or name:1-6,9,12-15"
            )
        name, spec = item.split(":", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"Invalid group name in '{item}'")
        indices = parse_index_spec(spec.strip(), natoms)
        groups.append((name, indices))
    return groups


def read_acf(acf_path: Path):
    """
    Read ACF.dat from the Henkelman Bader code.

    Expected data lines typically look like:
      1   x   y   z   charge   min_dist   atomic_vol

    We parse the first 5 columns and ignore footer lines like:
      NUMBER OF ELECTRONS:
      VACUUM CHARGE:
      VACUUM VOLUME:
    """
    rows = []
    with acf_path.open("r", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if set(s) <= {"-", " "}:
                continue
            upper = s.upper()
            if upper.startswith("VACUUM CHARGE") or upper.startswith("VACUUM VOLUME") or upper.startswith("NUMBER OF ELECTRONS"):
                continue

            parts = s.split()
            if len(parts) < 5:
                continue
            try:
                idx = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])
                z = float(parts[3])
                charge = float(parts[4])
            except ValueError:
                continue

            rows.append({
                "acf_index": idx,
                "x": x,
                "y": y,
                "z": z,
                "bader_electrons": charge,
            })

    if not rows:
        raise ValueError("No atomic rows could be read from ACF.dat")

    return rows


def composition_string(symbols):
    comp = dict(sorted(Counter(symbols).items(), key=lambda x: x[0]))
    return " ".join(f"{el}:{n}" for el, n in comp.items())


def build_atom_rows(atoms, acf_rows, refs):
    if len(atoms) != len(acf_rows):
        raise ValueError(
            f"Mismatch between structure ({len(atoms)} atoms) and ACF.dat ({len(acf_rows)} rows)"
        )

    atom_rows = []
    for i, (atom, acf) in enumerate(zip(atoms, acf_rows), start=1):
        symbol = atom.symbol
        ref_val = refs.get(symbol)
        bader_e = acf["bader_electrons"]
        net_charge = (ref_val - bader_e) if ref_val is not None else None

        atom_rows.append(
            {
                "index": i,
                "symbol": symbol,
                "x": atom.position[0],
                "y": atom.position[1],
                "z": atom.position[2],
                "acf_x": acf["x"],
                "acf_y": acf["y"],
                "acf_z": acf["z"],
                "bader_electrons": bader_e,
                "reference_valence": ref_val,
                "net_charge": net_charge,
            }
        )
    return atom_rows


def build_group_rows(atom_rows, groups):
    group_rows = []
    for name, indices0 in groups:
        members = [atom_rows[i] for i in indices0]
        total_bader = sum(r["bader_electrons"] for r in members)

        ref_values = [r["reference_valence"] for r in members]
        total_ref = None if any(v is None for v in ref_values) else sum(ref_values)

        net_values = [r["net_charge"] for r in members]
        total_net = None if any(v is None for v in net_values) else sum(net_values)

        formula_counter = Counter(r["symbol"] for r in members)
        formula = " ".join(f"{el}:{n}" for el, n in sorted(formula_counter.items()))

        group_rows.append(
            {
                "group": name,
                "natoms": len(members),
                "formula": formula,
                "indices_1based": ",".join(str(i + 1) for i in indices0),
                "total_bader_electrons": total_bader,
                "total_reference_valence": total_ref,
                "total_net_charge": total_net,
            }
        )
    return group_rows


def write_atoms_csv(path, atom_rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "index",
                "symbol",
                "x_A",
                "y_A",
                "z_A",
                "acf_x_A",
                "acf_y_A",
                "acf_z_A",
                "bader_electrons",
                "reference_valence",
                "net_charge",
            ]
        )
        for r in atom_rows:
            writer.writerow(
                [
                    r["index"],
                    r["symbol"],
                    r["x"],
                    r["y"],
                    r["z"],
                    r["acf_x"],
                    r["acf_y"],
                    r["acf_z"],
                    r["bader_electrons"],
                    r["reference_valence"],
                    r["net_charge"],
                ]
            )


def write_groups_csv(path, group_rows):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "group",
                "natoms",
                "formula",
                "indices_1based",
                "total_bader_electrons",
                "total_reference_valence",
                "total_net_charge",
            ]
        )
        for r in group_rows:
            writer.writerow(
                [
                    r["group"],
                    r["natoms"],
                    r["formula"],
                    r["indices_1based"],
                    r["total_bader_electrons"],
                    r["total_reference_valence"],
                    r["total_net_charge"],
                ]
            )


def format_float_or_na(x, nd=6):
    return "n/a" if x is None else f"{x:.{nd}f}"


def build_summary_text(acf_path, structure_path, atoms, refs, atom_rows, groups, group_rows):
    lines = []
    lines.append("Bader summary")
    lines.append("=============")
    lines.append("")
    lines.append(f"ACF file: {acf_path}")
    lines.append(f"Structure file: {structure_path}")
    lines.append("")
    lines.append("System")
    lines.append("------")
    lines.append(f"Number of atoms: {len(atoms)}")
    lines.append(f"Composition: {composition_string(atoms.get_chemical_symbols())}")
    lines.append("")
    lines.append("Reference valence electrons")
    lines.append("---------------------------")
    if refs:
        for el in sorted(refs):
            lines.append(f"{el}: {refs[el]:.6f}")
    else:
        lines.append("No reference valence electrons provided.")
        lines.append("Net charges will be reported as n/a.")

    lines.append("")
    lines.append("Per-atom Bader data")
    lines.append("-------------------")
    lines.append(
        " idx  el         x(A)         y(A)         z(A)    bader_e     ref_val    net_charge"
    )
    for r in atom_rows:
        lines.append(
            f"{r['index']:4d}  {r['symbol']:>2s}  "
            f"{r['x']:11.6f}  {r['y']:11.6f}  {r['z']:11.6f}  "
            f"{r['bader_electrons']:10.6f}  {format_float_or_na(r['reference_valence']):>9s}  "
            f"{format_float_or_na(r['net_charge']):>10s}"
        )

    lines.append("")
    lines.append("Element-wise averages")
    lines.append("---------------------")
    by_el = {}
    for r in atom_rows:
        by_el.setdefault(r["symbol"], []).append(r)
    for el in sorted(by_el):
        subset = by_el[el]
        avg_bader = sum(x["bader_electrons"] for x in subset) / len(subset)
        ref_val = subset[0]["reference_valence"]
        if ref_val is None:
            avg_net = None
        else:
            avg_net = sum(x["net_charge"] for x in subset) / len(subset)
        lines.append(
            f"{el:>2s}: natoms={len(subset):4d}  avg_bader={avg_bader:10.6f}  avg_net={format_float_or_na(avg_net)}"
        )

    if groups:
        lines.append("")
        lines.append("Group sums")
        lines.append("----------")
        lines.append(
            " group              natoms   formula                   total_bader    total_ref    total_net"
        )
        for r in group_rows:
            lines.append(
                f" {r['group']:<18s} {r['natoms']:6d}   {r['formula']:<22s} "
                f"{r['total_bader_electrons']:11.6f}  {format_float_or_na(r['total_reference_valence']):>9s}  "
                f"{format_float_or_na(r['total_net_charge']):>9s}"
            )

    lines.append("")
    lines.append("Notes")
    lines.append("-----")
    lines.append("- net_charge = reference_valence - bader_electrons")
    lines.append("- Net charges are only meaningful if suitable reference valence values are supplied.")
    lines.append("- This script assumes the atom order in ACF.dat matches the structure file.")

    return "\n".join(lines) + "\n"


def main():
    args = parse_args()

    acf_path = Path(args.acf)
    structure_path = Path(args.structure)

    if not acf_path.is_file():
        print(f"ERROR: ACF file not found: {acf_path}")
        sys.exit(1)
    if not structure_path.is_file():
        print(f"ERROR: structure file not found: {structure_path}")
        sys.exit(1)

    try:
        refs = parse_ref_list(args.ref)
    except Exception as exc:
        print(f"ERROR while parsing --ref: {exc}")
        sys.exit(1)

    try:
        atoms = read(str(structure_path))
    except Exception as exc:
        print(f"ERROR: could not read structure with ASE: {exc}")
        sys.exit(1)

    try:
        acf_rows = read_acf(acf_path)
    except Exception as exc:
        print(f"ERROR: could not read ACF.dat: {exc}")
        sys.exit(1)

    try:
        atom_rows = build_atom_rows(atoms, acf_rows, refs)
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    try:
        groups = parse_groups(args.groups, len(atoms)) if args.groups else []
    except Exception as exc:
        print(f"ERROR while parsing --groups: {exc}")
        sys.exit(1)

    group_rows = build_group_rows(atom_rows, groups) if groups else []

    summary_text = build_summary_text(
        acf_path=acf_path,
        structure_path=structure_path,
        atoms=atoms,
        refs=refs,
        atom_rows=atom_rows,
        groups=groups,
        group_rows=group_rows,
    )

    print(summary_text, end="")

    with open(args.summary, "w") as f:
        f.write(summary_text)
    write_atoms_csv(args.atoms_csv, atom_rows)
    if groups:
        write_groups_csv(args.groups_csv, group_rows)

    print(f"Summary written to: {args.summary}")
    print(f"Atom CSV written to: {args.atoms_csv}")
    if groups:
        print(f"Group CSV written to: {args.groups_csv}")


if __name__ == "__main__":
    main()
