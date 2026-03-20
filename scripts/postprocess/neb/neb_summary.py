#!/usr/bin/env python3
"""
neb_summary.py

Summarize NEB image energies from numbered folders (00, 01, 02, ...).

By default:
- tries to read the last E0 from OSZICAR
- if that fails, tries OUTCAR
- writes neb_summary.dat and neb_summary.csv
- optionally plots neb_profile.png

Examples
--------
python3 neb_summary.py
python3 neb_summary.py --plot
python3 neb_summary.py --source outcar
python3 neb_summary.py --ref min --plot
python3 neb_summary.py --root /path/to/neb --plot
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Summarize NEB energies from numbered image folders."
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Root directory containing NEB image folders (default: current directory).",
    )
    parser.add_argument(
        "--source",
        choices=["auto", "oszicar", "outcar"],
        default="auto",
        help="Energy source: auto, oszicar, or outcar (default: auto).",
    )
    parser.add_argument(
        "--ref",
        choices=["first", "min", "last"],
        default="first",
        help="Reference for relative energies (default: first).",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Generate neb_profile.png using matplotlib.",
    )
    parser.add_argument(
        "--digits-only",
        action="store_true",
        help="Only consider directories with names made exclusively of digits.",
    )
    return parser.parse_args()


def find_image_dirs(root: Path, digits_only: bool = False):
    dirs = []
    for p in root.iterdir():
        if not p.is_dir():
            continue
        if digits_only:
            if re.fullmatch(r"\d+", p.name):
                dirs.append(p)
        else:
            # still prioritize VASP-NEB style numeric folders
            if re.fullmatch(r"\d+", p.name):
                dirs.append(p)

    dirs.sort(key=lambda x: int(x.name))
    return dirs


def read_last_oszicar_energy(path: Path):
    """
    Read the last E0 from OSZICAR.
    Returns float or None.
    """
    if not path.is_file():
        return None

    energy = None
    pattern = re.compile(r"E0=\s*([-\d.Ee+]+)")
    try:
        with path.open("r", errors="ignore") as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    energy = float(m.group(1))
    except Exception:
        return None

    return energy


def read_last_outcar_energy(path: Path):
    """
    Read a final energy from OUTCAR.
    Preference:
    1) 'energy  without entropy='
    2) 'free  energy   TOTEN  ='
    Returns float or None.
    """
    if not path.is_file():
        return None

    e_wo_entropy = None
    e_toten = None

    pat_wo = re.compile(r"energy\s+without entropy=\s*([-\d.Ee+]+)")
    pat_toten = re.compile(r"TOTEN\s*=\s*([-\d.Ee+]+)")

    try:
        with path.open("r", errors="ignore") as f:
            for line in f:
                m1 = pat_wo.search(line)
                if m1:
                    e_wo_entropy = float(m1.group(1))

                if "free  energy   TOTEN" in line:
                    m2 = pat_toten.search(line)
                    if m2:
                        e_toten = float(m2.group(1))
    except Exception:
        return None

    if e_wo_entropy is not None:
        return e_wo_entropy
    return e_toten


def read_energy(image_dir: Path, source: str):
    oszicar = image_dir / "OSZICAR"
    outcar = image_dir / "OUTCAR"

    if source == "oszicar":
        e = read_last_oszicar_energy(oszicar)
        return e, "OSZICAR" if e is not None else "missing"

    if source == "outcar":
        e = read_last_outcar_energy(outcar)
        return e, "OUTCAR" if e is not None else "missing"

    # auto
    e = read_last_oszicar_energy(oszicar)
    if e is not None:
        return e, "OSZICAR"

    e = read_last_outcar_energy(outcar)
    if e is not None:
        return e, "OUTCAR"

    return None, "missing"


def get_reference_energy(energies, ref_mode):
    valid = [e for e in energies if e is not None]
    if not valid:
        raise ValueError("No valid energies found.")

    if ref_mode == "first":
        for e in energies:
            if e is not None:
                return e
        raise ValueError("No valid first energy found.")

    if ref_mode == "last":
        for e in reversed(energies):
            if e is not None:
                return e
        raise ValueError("No valid last energy found.")

    if ref_mode == "min":
        return min(valid)

    raise ValueError(f"Unknown reference mode: {ref_mode}")


def write_outputs(rows, root: Path):
    dat_path = root / "neb_summary.dat"
    csv_path = root / "neb_summary.csv"

    with dat_path.open("w") as f:
        f.write("# image  energy_eV  relative_eV  source\n")
        for row in rows:
            img = row["image"]
            ene = row["energy_eV"]
            rel = row["relative_eV"]
            src = row["source"]

            ene_str = f"{ene:.8f}" if ene is not None else "nan"
            rel_str = f"{rel:.8f}" if rel is not None else "nan"
            f.write(f"{img:>4s}  {ene_str:>14s}  {rel_str:>14s}  {src}\n")

    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["image", "energy_eV", "relative_eV", "source"])
        for row in rows:
            writer.writerow(
                [row["image"], row["energy_eV"], row["relative_eV"], row["source"]]
            )

    return dat_path, csv_path


def make_plot(rows, root: Path):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("WARNING: matplotlib is not installed. Skipping plot.")
        return None

    x = []
    y = []
    labels = []

    for i, row in enumerate(rows):
        if row["relative_eV"] is None:
            continue
        x.append(i)
        y.append(row["relative_eV"])
        labels.append(row["image"])

    if not x:
        print("WARNING: no valid energies available for plotting.")
        return None

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x, y, marker="o")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("NEB image")
    ax.set_ylabel("Relative energy (eV)")
    ax.set_title("NEB energy profile")
    ax.grid(True, alpha=0.3)

    png_path = root / "neb_profile.png"
    fig.tight_layout()
    fig.savefig(png_path, dpi=200)
    plt.close(fig)

    return png_path


def main():
    args = parse_args()
    root = Path(args.root).resolve()

    if not root.is_dir():
        print(f"ERROR: root directory does not exist: {root}")
        sys.exit(1)

    image_dirs = find_image_dirs(root, digits_only=args.digits_only)

    if not image_dirs:
        print("ERROR: no numbered image directories found.")
        sys.exit(1)

    rows = []
    energies = []

    for d in image_dirs:
        e, src = read_energy(d, args.source)
        energies.append(e)
        rows.append(
            {
                "image": d.name,
                "energy_eV": e,
                "relative_eV": None,
                "source": src,
            }
        )

    try:
        e_ref = get_reference_energy(energies, args.ref)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    valid_rows = []
    for row in rows:
        if row["energy_eV"] is not None:
            row["relative_eV"] = row["energy_eV"] - e_ref
            valid_rows.append(row)

    if not valid_rows:
        print("ERROR: no valid energies found in any image.")
        sys.exit(1)

    rel_energies = [row["relative_eV"] for row in valid_rows]
    max_rel = max(rel_energies)

    first_valid_rel = next(row["relative_eV"] for row in rows if row["relative_eV"] is not None)
    last_valid_rel = next(row["relative_eV"] for row in reversed(rows) if row["relative_eV"] is not None)

    forward_barrier = max_rel - first_valid_rel
    reverse_barrier = max_rel - last_valid_rel

    dat_path, csv_path = write_outputs(rows, root)

    print("\nNEB summary")
    print("-----------")
    for row in rows:
        ene = row["energy_eV"]
        rel = row["relative_eV"]
        src = row["source"]

        ene_str = f"{ene:.8f}" if ene is not None else "nan"
        rel_str = f"{rel:.8f}" if rel is not None else "nan"
        print(f"{row['image']:>4s}   E = {ene_str:>14s} eV   dE = {rel_str:>12s} eV   [{src}]")

    print("\nBarriers")
    print("--------")
    print(f"Forward barrier: {forward_barrier:.8f} eV")
    print(f"Reverse barrier: {reverse_barrier:.8f} eV")
    print(f"Maximum relative energy: {max_rel:.8f} eV")

    print("\nFiles written")
    print("-------------")
    print(dat_path)
    print(csv_path)

    if args.plot:
        png_path = make_plot(rows, root)
        if png_path is not None:
            print(png_path)


if __name__ == "__main__":
    main()
