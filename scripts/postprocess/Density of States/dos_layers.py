#!/usr/bin/env python3
from __future__ import annotations
import argparse
from vasp_dos_tools import read_metadata, make_z_groups, atom_species_map


def main():
    ap = argparse.ArgumentParser(description="Group atoms into slab layers according to z coordinate.")
    ap.add_argument("--doscar", default="DOSCAR")
    ap.add_argument("--outcar", default="OUTCAR")
    ap.add_argument("--contcar", default="CONTCAR")
    ap.add_argument("--tol", type=float, default=0.15, help="Grouping tolerance in angstrom.")
    args = ap.parse_args()

    meta = read_metadata(args.doscar, args.outcar, args.contcar)
    groups = make_z_groups(meta, tol=args.tol)
    sp_map = atom_species_map(meta)
    for i, group in enumerate(groups, start=1):
        atoms = group["atoms"]
        by_species = {}
        for atom in atoms:
            sp = sp_map.get(atom, "X")
            by_species.setdefault(sp, []).append(atom)
        print(f"Layer {i:02d} | z_avg = {group['z_avg']:.3f} A | atoms = {len(atoms)} | species = {','.join(group['species'])}")
        print("  " + " ; ".join(f"{sp}: {','.join(map(str, idxs))}" for sp, idxs in by_species.items()))


if __name__ == "__main__":
    main()
