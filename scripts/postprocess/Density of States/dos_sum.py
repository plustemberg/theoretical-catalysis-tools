#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from vasp_dos_tools import (
    read_metadata,
    parse_atom_selection,
    read_projected_atoms,
    sum_selected_columns,
    atom_species_map,
)


def main():
    ap = argparse.ArgumentParser(description="Sum PDOS over arbitrary atom selections and orbital groups.")
    ap.add_argument("--doscar", default="DOSCAR")
    ap.add_argument("--outcar", default="OUTCAR")
    ap.add_argument("--contcar", default="CONTCAR")
    ap.add_argument("--atoms", required=True, help="Selection like '1,2,5-8' or 'Mg' or '1-8,O'.")
    ap.add_argument("--orbitals", default=None, help="Comma-separated output groups, e.g. 's,p,d' or 'dz2,dxz,dx2-y2' or 'd_up,d_down'. Default: grouped s/p/d/f.")
    ap.add_argument("--output", default="DOS_sum.dat")
    args = ap.parse_args()

    meta = read_metadata(args.doscar, args.outcar, args.contcar)
    atoms = parse_atom_selection(args.atoms, meta)
    energies, labels, atom_data, _ = read_projected_atoms(atoms, args.doscar, args.outcar, args.contcar)
    orbitals = [x.strip() for x in args.orbitals.split(",")] if args.orbitals else None
    grouped = sum_selected_columns(labels, atom_data, orbitals)

    species_map = atom_species_map(meta)
    with Path(args.output).open("w") as fh:
        fh.write(f"# atoms: {' '.join(map(str, atoms))}\n")
        if species_map:
            fh.write("# species_per_atom: " + " ".join(f"{a}:{species_map[a]}" for a in atoms) + "\n")
        fh.write("# E-Ef(eV) " + " ".join(grouped.keys()) + "\n")
        for i, e in enumerate(energies):
            row = " ".join(f"{grouped[key][i]:.8f}" for key in grouped)
            fh.write(f"{e:12.6f} {row}\n")
    print(f"Written {args.output}")


if __name__ == "__main__":
    main()
