#!/usr/bin/env python3
"""
bader_compare.py

Compare Bader charges between two calculations.

Inputs
------
- ACF.dat from calculation 1
- structure file (POSCAR/CONTCAR) for calculation 1
- ACF.dat from calculation 2
- structure file (POSCAR/CONTCAR) for calculation 2

Outputs
-------
- bader_compare_atoms.csv
- bader_compare_groups.csv (if --groups is used)
- bader_compare_summary.txt

Notes
-----
- This version assumes atom-by-atom correspondence between both calculations.
- Therefore, atom order should be the same in both structures.
- Definitions used:
    delta_bader_electrons = bader(calc2) - bader(calc1)
    net_charge = ref_valence - bader_electrons
    delta_net_charge = net_charge(calc2) - net_charge(calc1)
                     = - delta_bader_electrons
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from ase.io import read


def parse_args():
    p = argparse.ArgumentParser(description="Compare Bader charges between two calculations.")
    p.add_argument("--acf1", required=True, help="ACF.dat from calculation 1")
    p.add_argument("--structure1", required=True, help="Structure file for calculation 1")
    p.add_argument("--acf2", required=True, help="ACF.dat from calculation 2")
    p.add_argument("--structure2", required=True, help="Structure file for calculation 2")
    p.add_argument(
        "--ref",
        nargs="*",
        default=[],
        help="Reference valence electrons by element, e.g. Ce=12 O=6 Ni=10 C=4 H=1",
    )
    p.add_argument(
        "--groups",
        nargs="*",
        default=[],
        help=(
            "Groups defined with 1-based indices, e.g. "
            "cluster:1-6 support:7-120 ads:121-126 or mix:1-3,8,10-12"
        ),
    )
    p.add_argument(
        "--csv-atoms",
        default="bader_compare_atoms.csv",
        help="Output CSV for atom-by-atom comparison (default: bader_compare_atoms.csv)",
    )
    p.add_argument(
        "--csv-groups",
        default="bader_compare_groups.csv",
        help="Output CSV for group comparison (default: bader_compare_groups.csv)",
    )
    p.add_argument(
        "--summary",
        default="bader_compare_summary.txt",
        help="Output text summary (default: bader_compare_summary.txt)",
    )
    return p.parse_args()


def composition(symbols):
    return dict(sorted(Counter(symbols).items()))


def composition_string(symbols):
    return " ".join(f"{k}:{v}" for k, v in composition(symbols).items())


def parse_ref_list(ref_items):
    ref = {}
    for item in ref_items:
        if "=" not in item:
            raise ValueError(f"Invalid reference specification '{item}'. Use Element=value")
        el, val = item.split("=", 1)
        el = el.strip()
        if not el:
            raise ValueError(f"Invalid element name in '{item}'")
        ref[el] = float(val)
    return ref


def expand_index_expr(expr, natoms):
    idx = []
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            i = int(a)
            j = int(b)
            if i > j:
                raise ValueError(f"Invalid range '{part}'")
            idx.extend(range(i, j + 1))
        else:
            idx.append(int(part))

    cleaned = []
    seen = set()
    for i in idx:
        if i < 1 or i > natoms:
            raise ValueError(f"Index {i} out of range for natoms={natoms}")
        if i not in seen:
            cleaned.append(i)
            seen.add(i)
    return cleaned


def parse_groups(group_items, natoms):
    groups = {}
    for item in group_items:
        if ":" not in item:
            raise ValueError(f"Invalid group specification '{item}'. Use name:indices")
        name, expr = item.split(":", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"Invalid empty group name in '{item}'")
        groups[name] = expand_index_expr(expr, natoms)
    return groups


def _is_data_line(line):
    s = line.strip()
    if not s or s.startswith("#"):
        return False
    if set(s) <= {"-"}:
        return False
    toks = s.split()
    if len(toks) < 5:
        return False
    try:
        int(toks[0])
        float(toks[1])
        float(toks[2])
        float(toks[3])
        float(toks[4])
        return True
    except Exception:
        return False


def read_acf(acf_path: Path):
    """
    Parse ACF.dat. Returns a dict with keys:
      index_1based, x, y, z, bader_electrons

    Works with the standard Henkelman-style ACF.dat where the first numeric lines
    correspond to atoms and later summary lines (VACUUM CHARGE, etc.) are ignored.
    """
    if not acf_path.is_file():
        raise FileNotFoundError(f"File not found: {acf_path}")

    rows = []
    with acf_path.open("r", errors="ignore") as f:
        for line in f:
            if not _is_data_line(line):
                continue
            toks = line.split()
            rows.append(
                {
                    "index_1based": int(toks[0]),
                    "x": float(toks[1]),
                    "y": float(toks[2]),
                    "z": float(toks[3]),
                    "bader_electrons": float(toks[4]),
                }
            )
    if not rows:
        raise ValueError(f"No atomic data lines found in {acf_path}")
    return rows


def build_atom_rows(atoms1, atoms2, acf1_rows, acf2_rows, ref_dict):
    natoms = len(atoms1)
    if len(acf1_rows) != natoms:
        raise ValueError(
            f"ACF1 has {len(acf1_rows)} atoms but structure1 has {natoms} atoms"
        )
    if len(acf2_rows) != natoms:
        raise ValueError(
            f"ACF2 has {len(acf2_rows)} atoms but structure2 has {natoms} atoms"
        )

    rows = []
    for i in range(natoms):
        sym1 = atoms1[i].symbol
        sym2 = atoms2[i].symbol

        q1 = acf1_rows[i]["bader_electrons"]
        q2 = acf2_rows[i]["bader_electrons"]
        dq = q2 - q1

        ref1 = ref_dict.get(sym1, None)
        ref2 = ref_dict.get(sym2, None)

        net1 = None if ref1 is None else ref1 - q1
        net2 = None if ref2 is None else ref2 - q2
        dnet = None if (net1 is None or net2 is None) else net2 - net1

        rows.append(
            {
                "index_1based": i + 1,
                "symbol1": sym1,
                "symbol2": sym2,
                "bader1_e": q1,
                "bader2_e": q2,
                "delta_bader_e": dq,
                "ref1_e": ref1,
                "ref2_e": ref2,
                "net1_e": net1,
                "net2_e": net2,
                "delta_net_e": dnet,
            }
        )
    return rows


def group_summary(atom_rows, groups):
    group_rows = []
    for name, idx_1based in groups.items():
        sel = [atom_rows[i - 1] for i in idx_1based]
        b1 = sum(r["bader1_e"] for r in sel)
        b2 = sum(r["bader2_e"] for r in sel)
        db = sum(r["delta_bader_e"] for r in sel)

        have_net = all(r["net1_e"] is not None and r["net2_e"] is not None for r in sel)
        if have_net:
            n1 = sum(r["net1_e"] for r in sel)
            n2 = sum(r["net2_e"] for r in sel)
            dn = sum(r["delta_net_e"] for r in sel)
        else:
            n1 = None
            n2 = None
            dn = None

        group_rows.append(
            {
                "group": name,
                "n_atoms": len(sel),
                "bader1_e": b1,
                "bader2_e": b2,
                "delta_bader_e": db,
                "net1_e": n1,
                "net2_e": n2,
                "delta_net_e": dn,
                "indices": ",".join(str(i) for i in idx_1based),
            }
        )
    return group_rows


def write_atom_csv(path, atom_rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "index_1based",
                "symbol1",
                "symbol2",
                "bader1_e",
                "bader2_e",
                "delta_bader_e",
                "ref1_e",
                "ref2_e",
                "net1_e",
                "net2_e",
                "delta_net_e",
            ]
        )
        for r in atom_rows:
            w.writerow(
                [
                    r["index_1based"],
                    r["symbol1"],
                    r["symbol2"],
                    r["bader1_e"],
                    r["bader2_e"],
                    r["delta_bader_e"],
                    r["ref1_e"],
                    r["ref2_e"],
                    r["net1_e"],
                    r["net2_e"],
                    r["delta_net_e"],
                ]
            )


def write_group_csv(path, group_rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "group",
                "n_atoms",
                "bader1_e",
                "bader2_e",
                "delta_bader_e",
                "net1_e",
                "net2_e",
                "delta_net_e",
                "indices",
            ]
        )
        for r in group_rows:
            w.writerow(
                [
                    r["group"],
                    r["n_atoms"],
                    r["bader1_e"],
                    r["bader2_e"],
                    r["delta_bader_e"],
                    r["net1_e"],
                    r["net2_e"],
                    r["delta_net_e"],
                    r["indices"],
                ]
            )


def fmt(x):
    return "nan" if x is None else f"{x:.6f}"


def build_summary_text(args, atoms1, atoms2, atom_rows, group_rows, ref_dict):
    sym1 = atoms1.get_chemical_symbols()
    sym2 = atoms2.get_chemical_symbols()

    same_natoms = len(atoms1) == len(atoms2)
    same_comp = composition(sym1) == composition(sym2)
    same_order = list(sym1) == list(sym2)

    lines = []
    lines.append("Bader charge comparison")
    lines.append("=======================")
    lines.append("")
    lines.append(f"Calculation 1 ACF:       {args.acf1}")
    lines.append(f"Calculation 1 structure: {args.structure1}")
    lines.append(f"Calculation 2 ACF:       {args.acf2}")
    lines.append(f"Calculation 2 structure: {args.structure2}")
    lines.append("")
    lines.append("General checks")
    lines.append("--------------")
    lines.append(f"natoms calc1: {len(atoms1)}")
    lines.append(f"natoms calc2: {len(atoms2)}")
    lines.append(f"same natoms: {same_natoms}")
    lines.append(f"composition calc1: {composition_string(sym1)}")
    lines.append(f"composition calc2: {composition_string(sym2)}")
    lines.append(f"same composition: {same_comp}")
    lines.append(f"same atom order: {same_order}")
    lines.append("")
    lines.append("Reference valence dictionary")
    lines.append("----------------------------")
    if ref_dict:
        for k in sorted(ref_dict):
            lines.append(f"{k}: {ref_dict[k]:.6f}")
    else:
        lines.append("No reference valence dictionary provided. Net charges were not computed.")

    lines.append("")
    lines.append("Atom-by-atom comparison")
    lines.append("-----------------------")
    lines.append(
        " idx  s1  s2   Bader1(e)    Bader2(e)   dBader(e)     Net1(e)      Net2(e)      dNet(e)"
    )
    for r in atom_rows:
        lines.append(
            f"{r['index_1based']:4d}  {r['symbol1']:>2s}  {r['symbol2']:>2s}  "
            f"{r['bader1_e']:11.6f}  {r['bader2_e']:11.6f}  {r['delta_bader_e']:10.6f}  "
            f"{fmt(r['net1_e']):>11s}  {fmt(r['net2_e']):>11s}  {fmt(r['delta_net_e']):>11s}"
        )

    total_db = sum(r["delta_bader_e"] for r in atom_rows)
    lines.append("")
    lines.append("Totals")
    lines.append("------")
    lines.append(f"Sum of delta_bader_e over all atoms: {total_db:.6f} e")
    if all(r["delta_net_e"] is not None for r in atom_rows):
        total_dn = sum(r["delta_net_e"] for r in atom_rows)
        lines.append(f"Sum of delta_net_e over all atoms:   {total_dn:.6f} e")

    if group_rows:
        lines.append("")
        lines.append("Group comparison")
        lines.append("----------------")
        lines.append(
            " group              n_atoms   Bader1(e)    Bader2(e)   dBader(e)     Net1(e)      Net2(e)      dNet(e)"
        )
        for r in group_rows:
            lines.append(
                f"{r['group']:<18s} {r['n_atoms']:6d}  {r['bader1_e']:11.6f}  {r['bader2_e']:11.6f}  {r['delta_bader_e']:10.6f}  "
                f"{fmt(r['net1_e']):>11s}  {fmt(r['net2_e']):>11s}  {fmt(r['delta_net_e']):>11s}"
            )

    lines.append("")
    lines.append("Definitions")
    lines.append("-----------")
    lines.append("delta_bader_e = Bader(calc2) - Bader(calc1)")
    lines.append("net_charge = reference_valence - bader_electrons")
    lines.append("delta_net_e = net_charge(calc2) - net_charge(calc1)")
    lines.append("")
    lines.append("Important note")
    lines.append("--------------")
    lines.append(
        "This script assumes atom-by-atom correspondence between both calculations. "
        "If the atom order changed, the comparison is not meaningful unless atoms are remapped first."
    )

    return "\n".join(lines) + "\n"


def main():
    args = parse_args()

    try:
        ref_dict = parse_ref_list(args.ref)
    except Exception as exc:
        print(f"ERROR parsing --ref: {exc}")
        sys.exit(1)

    try:
        atoms1 = read(args.structure1)
        atoms2 = read(args.structure2)
    except Exception as exc:
        print(f"ERROR reading structures: {exc}")
        sys.exit(1)

    if len(atoms1) != len(atoms2):
        print("ERROR: the two structures do not have the same number of atoms.")
        sys.exit(1)

    try:
        acf1_rows = read_acf(Path(args.acf1))
        acf2_rows = read_acf(Path(args.acf2))
    except Exception as exc:
        print(f"ERROR reading ACF files: {exc}")
        sys.exit(1)

    try:
        atom_rows = build_atom_rows(atoms1, atoms2, acf1_rows, acf2_rows, ref_dict)
    except Exception as exc:
        print(f"ERROR building atom comparison: {exc}")
        sys.exit(1)

    try:
        groups = parse_groups(args.groups, len(atoms1)) if args.groups else {}
        group_rows = group_summary(atom_rows, groups) if groups else []
    except Exception as exc:
        print(f"ERROR processing groups: {exc}")
        sys.exit(1)

    summary_text = build_summary_text(args, atoms1, atoms2, atom_rows, group_rows, ref_dict)
    print(summary_text, end="")

    write_atom_csv(args.csv_atoms, atom_rows)
    with open(args.summary, "w") as f:
        f.write(summary_text)

    print(f"Atom comparison written to: {args.csv_atoms}")
    print(f"Summary written to: {args.summary}")

    if group_rows:
        write_group_csv(args.csv_groups, group_rows)
        print(f"Group comparison written to: {args.csv_groups}")


if __name__ == "__main__":
    main()
