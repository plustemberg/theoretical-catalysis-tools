#!/usr/bin/env python3
from __future__ import annotations
import argparse
from vasp_dos_tools import read_total_dos, estimate_gap


def main():
    ap = argparse.ArgumentParser(description="Estimate VBM/CBM/gap from the total DOS using a simple threshold.")
    ap.add_argument("--doscar", default="DOSCAR")
    ap.add_argument("--threshold", type=float, default=1e-3, help="DOS threshold used to define band edges.")
    args = ap.parse_args()

    energies, labels, cols, meta = read_total_dos(args.doscar)
    if "dos" in labels:
        dos = cols[labels.index("dos")]
    elif "dos_up" in labels and "dos_down" in labels:
        up = cols[labels.index("dos_up")]
        down = cols[labels.index("dos_down")]
        dos = [u + d for u, d in zip(up, down)]
    else:
        raise ValueError("Could not identify the total DOS columns.")

    out = estimate_gap(energies, dos, threshold=args.threshold)
    print(f"threshold : {args.threshold:g}")
    print(f"VBM       : {out['VBM']:.6f} eV")
    print(f"CBM       : {out['CBM']:.6f} eV")
    print(f"gap       : {out['gap']:.6f} eV")


if __name__ == "__main__":
    main()
