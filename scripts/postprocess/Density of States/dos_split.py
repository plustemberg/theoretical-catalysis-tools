#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from vasp_dos_tools import read_total_dos, read_projected_atoms, read_metadata, projected_labels, total_labels


def write_table(path: Path, energies, labels, cols):
    with path.open("w") as fh:
        fh.write("# E-Ef(eV) " + " ".join(labels) + "\n")
        for i, e in enumerate(energies):
            values = " ".join(f"{col[i]:.8f}" for col in cols)
            fh.write(f"{e:12.6f} {values}\n")


def main():
    ap = argparse.ArgumentParser(description="Export total DOS and/or atom-resolved PDOS to plain text.")
    ap.add_argument("--doscar", default="DOSCAR")
    ap.add_argument("--outcar", default="OUTCAR")
    ap.add_argument("--contcar", default="CONTCAR")
    ap.add_argument("--outdir", default="dos_export")
    ap.add_argument("--atoms", default=None, help="Atom selection, e.g. '1,2,5-8' or 'Mg,O'. Default: all atoms.")
    ap.add_argument("--total-only", action="store_true", help="Write only the total DOS.")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    energies, labels, cols, meta_total = read_total_dos(args.doscar)
    write_table(outdir / "DOS_total.dat", energies, labels, cols)

    meta = read_metadata(args.doscar, args.outcar, args.contcar)
    if not args.total_only and meta.proj_ncols is not None:
        if args.atoms:
            from vasp_dos_tools import parse_atom_selection
            atoms = parse_atom_selection(args.atoms, meta)
        else:
            atoms = list(range(1, meta.natoms + 1))
        p_energies, p_labels, atom_data, _ = read_projected_atoms(atoms, args.doscar, args.outcar, args.contcar)
        for atom in atoms:
            write_table(outdir / f"atom_{atom}.dat", p_energies, p_labels, atom_data[atom])

    print(f"Files written to: {outdir}")


if __name__ == "__main__":
    main()
