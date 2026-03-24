#!/usr/bin/env python3
from __future__ import annotations
import argparse
import math
from vasp_dos_tools import (
    read_metadata,
    parse_atom_selection,
    read_projected_atoms,
    sum_selected_columns,
    band_center,
    integrate_window,
)


def main():
    ap = argparse.ArgumentParser(description="Compute DOS metrics such as band centers and integrated weights in an energy window.")
    ap.add_argument("--doscar", default="DOSCAR")
    ap.add_argument("--outcar", default="OUTCAR")
    ap.add_argument("--contcar", default="CONTCAR")
    ap.add_argument("--atoms", required=True, help="Atom selection like '1-4' or 'Mg' or '33-64'.")
    ap.add_argument("--orbitals", required=True, help="Comma-separated orbital groups, e.g. 'd' or 'p,d' or 'dz2'.")
    ap.add_argument("--emin", type=float, required=True)
    ap.add_argument("--emax", type=float, required=True)
    args = ap.parse_args()

    meta = read_metadata(args.doscar, args.outcar, args.contcar)
    atoms = parse_atom_selection(args.atoms, meta)
    energies, labels, atom_data, _ = read_projected_atoms(atoms, args.doscar, args.outcar, args.contcar)
    orbitals = [x.strip() for x in args.orbitals.split(",") if x.strip()]
    grouped = sum_selected_columns(labels, atom_data, orbitals)

    print(f"# atoms    : {atoms}")
    print(f"# window   : [{args.emin:.3f}, {args.emax:.3f}] eV relative to Ef")
    print(f"# columns  : orbital integral band_center")
    for key, values in grouped.items():
        integ = integrate_window(energies, values, args.emin, args.emax)
        center = band_center(energies, values, args.emin, args.emax)
        center_str = f"{center:.6f}" if not math.isnan(center) else "nan"
        print(f"{key:12s} {integ:14.6f} {center_str:14s}")


if __name__ == "__main__":
    main()
