#!/usr/bin/env python3
from __future__ import annotations
import argparse
from vasp_dos_tools import read_metadata, projected_labels, total_labels, atom_species_map


def main():
    ap = argparse.ArgumentParser(description="Print a compact summary of DOSCAR/OUTCAR/CONTCAR.")
    ap.add_argument("--doscar", default="DOSCAR")
    ap.add_argument("--outcar", default="OUTCAR")
    ap.add_argument("--contcar", default="CONTCAR")
    args = ap.parse_args()

    meta = read_metadata(args.doscar, args.outcar, args.contcar)
    print(f"DOSCAR   : {meta.doscar}")
    print(f"natoms   : {meta.natoms}")
    print(f"NEDOS    : {meta.nedos}")
    print(f"Efermi   : {meta.efermi:.6f} eV")
    print(f"ISPIN    : {meta.ispin}")
    print(f"LORBIT   : {meta.lorbit}")
    print(f"total cols    : {meta.total_ncols} -> {', '.join(total_labels(meta.total_ncols, meta.ispin))}")
    if meta.proj_ncols:
        print(f"projected cols: {meta.proj_ncols} -> {', '.join(projected_labels(meta.proj_ncols, meta.ispin))}")
    else:
        print("projected cols: none")

    if meta.species and meta.counts:
        print("species  : " + ", ".join(f"{sp}({n})" for sp, n in zip(meta.species, meta.counts)))
        sp_map = atom_species_map(meta)
        preview = []
        for atom in range(1, min(meta.natoms, 12) + 1):
            z = meta.z_cart[atom - 1] if meta.z_cart else float('nan')
            preview.append(f"{atom}:{sp_map.get(atom,'?')}@z={z:.3f}")
        print("atoms preview : " + "; ".join(preview))


if __name__ == "__main__":
    main()
