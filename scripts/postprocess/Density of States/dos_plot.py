#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
from vasp_dos_tools import (
    read_total_dos,
    read_metadata,
    parse_atom_selection,
    read_projected_atoms,
    sum_selected_columns,
)


def crop(energies, series, emin=None, emax=None):
    idx = [i for i, e in enumerate(energies) if (emin is None or e >= emin) and (emax is None or e <= emax)]
    e2 = [energies[i] for i in idx]
    s2 = {k: [v[i] for i in idx] for k, v in series.items()}
    return e2, s2


def main():
    ap = argparse.ArgumentParser(description="Quick DOS plotter for total DOS or selected projected DOS.")
    ap.add_argument("--doscar", default="DOSCAR")
    ap.add_argument("--outcar", default="OUTCAR")
    ap.add_argument("--contcar", default="CONTCAR")
    ap.add_argument("--atoms", default=None, help="If given, plot summed PDOS for selected atoms.")
    ap.add_argument("--orbitals", default=None, help="For PDOS plots: comma-separated groups, e.g. 's,p,d' or 'dz2,dxz'.")
    ap.add_argument("--emin", type=float, default=None)
    ap.add_argument("--emax", type=float, default=None)
    ap.add_argument("--output", default="dos_plot.png")
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    if args.atoms is None:
        energies, labels, cols, meta = read_total_dos(args.doscar)
        series = {}
        if "dos" in labels:
            series["total DOS"] = cols[labels.index("dos")]
        else:
            if "dos_up" in labels:
                series["DOS up"] = cols[labels.index("dos_up")]
            if "dos_down" in labels:
                series["DOS down"] = [-x for x in cols[labels.index("dos_down")]]
    else:
        meta = read_metadata(args.doscar, args.outcar, args.contcar)
        atoms = parse_atom_selection(args.atoms, meta)
        energies, labels, atom_data, _ = read_projected_atoms(atoms, args.doscar, args.outcar, args.contcar)
        orbitals = [x.strip() for x in args.orbitals.split(",")] if args.orbitals else None
        series = sum_selected_columns(labels, atom_data, orbitals)
        # Mirror spin-down channels if user explicitly requested them.
        for key in list(series):
            if key.lower().endswith("down"):
                series[key] = [-x for x in series[key]]

    energies, series = crop(energies, series, args.emin, args.emax)

    plt.figure(figsize=(7, 5))
    for label, values in series.items():
        plt.plot(energies, values, label=label)
    plt.axvline(0.0, linewidth=0.8)
    plt.axhline(0.0, linewidth=0.6)
    plt.xlabel(r"E - E$_F$ (eV)")
    plt.ylabel("DOS")
    if args.title:
        plt.title(args.title)
    if len(series) > 1:
        plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(args.output, dpi=200)
    print(f"Written {args.output}")


if __name__ == "__main__":
    main()
