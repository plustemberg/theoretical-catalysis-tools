#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Sequence, Tuple

MODE_LINE_RE = re.compile(
    r"^\s*(\d+)\s+f(?:/i)?\s*=\s*([-+]?\d*\.\d+|[-+]?\d+)\s+THz\s+"
    r"([-+]?\d*\.\d+|[-+]?\d+)\s+2PiTHz\s+"
    r"([-+]?\d*\.\d+|[-+]?\d+)\s+cm-1\s+"
    r"([-+]?\d*\.\d+|[-+]?\d+)\s+meV"
)

ATOM_LINE_RE = re.compile(
    r"^\s*([-+]?\d*\.\d+(?:[Ee][-+]?\d+)?|[-+]?\d+(?:[Ee][-+]?\d+)?)\s+"
    r"([-+]?\d*\.\d+(?:[Ee][-+]?\d+)?|[-+]?\d+(?:[Ee][-+]?\d+)?)\s+"
    r"([-+]?\d*\.\d+(?:[Ee][-+]?\d+)?|[-+]?\d+(?:[Ee][-+]?\d+)?)\s+"
    r"([-+]?\d*\.\d+(?:[Ee][-+]?\d+)?|[-+]?\d+(?:[Ee][-+]?\d+)?)\s+"
    r"([-+]?\d*\.\d+(?:[Ee][-+]?\d+)?|[-+]?\d+(?:[Ee][-+]?\d+)?)\s+"
    r"([-+]?\d*\.\d+(?:[Ee][-+]?\d+)?|[-+]?\d+(?:[Ee][-+]?\d+)?)\s*$"
)


def read_contcar_species(contcar_path: Path) -> Tuple[List[str], List[int], List[str]]:
    lines = contcar_path.read_text(encoding="utf-8", errors="replace").splitlines()

    if len(lines) < 7:
        raise ValueError(f"{contcar_path} is too short to be a valid CONTCAR/POSCAR file.")

    symbols_line = lines[5].split()
    counts_line = lines[6].split()

    try:
        counts = [int(x) for x in counts_line]
    except ValueError as exc:
        raise ValueError(
            "Could not parse atom counts from line 7 of CONTCAR. "
            "This script expects VASP 5-style CONTCAR/POSCAR "
            "(element symbols on line 6 and counts on line 7)."
        ) from exc

    if len(symbols_line) != len(counts):
        raise ValueError(
            "Mismatch between number of element symbols and atom counts in CONTCAR."
        )

    expanded_symbols: List[str] = []
    for symbol, count in zip(symbols_line, counts):
        expanded_symbols.extend([symbol] * count)

    return symbols_line, counts, expanded_symbols


def parse_outcar_modes(outcar_path: Path, natoms: int):
    lines = outcar_path.read_text(encoding="utf-8", errors="replace").splitlines()
    modes = []

    i = 0
    while i < len(lines):
        match = MODE_LINE_RE.match(lines[i])
        if not match:
            i += 1
            continue

        mode_index = int(match.group(1))
        thz = float(match.group(2))
        two_pi_thz = float(match.group(3))
        cm1 = float(match.group(4))
        mev = float(match.group(5))

        # La siguiente línea suele ser:
        # X Y Z dx dy dz
        data_start = i + 2

        atom_rows = []
        for j in range(data_start, data_start + natoms):
            if j >= len(lines):
                raise ValueError(
                    f"OUTCAR ended unexpectedly while reading mode {mode_index}."
                )

            atom_match = ATOM_LINE_RE.match(lines[j])
            if not atom_match:
                raise ValueError(
                    f"Could not parse atom line for mode {mode_index}:\n{lines[j]}"
                )

            atom_rows.append([float(atom_match.group(k)) for k in range(1, 7)])

        modes.append(
            {
                "mode_index": mode_index,
                "thz": thz,
                "two_pi_thz": two_pi_thz,
                "cm1": cm1,
                "mev": mev,
                "rows": atom_rows,
            }
        )

        i = data_start + natoms

    if not modes:
        raise ValueError(f"No vibrational modes were found in {outcar_path}.")

    return modes


def write_frequency_values(output_path: Path, modes: Sequence[dict]) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        for mode in modes:
            handle.write(
                f"{mode['mode_index']:4d}  {mode['thz']:12.6f} THz  "
                f"{mode['two_pi_thz']:12.6f} 2PiTHz  "
                f"{mode['cm1']:12.6f} cm-1  {mode['mev']:12.6f} meV\n"
            )


def write_xyz(output_path: Path, modes: Sequence[dict], symbols: Sequence[str]) -> None:
    natoms = len(symbols)

    with output_path.open("w", encoding="utf-8") as handle:
        for mode in modes:
            handle.write(f"{natoms}\n")
            handle.write(
                f"mode {mode['mode_index']} | {mode['thz']:.6f} THz | "
                f"{mode['cm1']:.6f} cm-1\n"
            )

            for symbol, row in zip(symbols, mode["rows"]):
                x, y, z, dx, dy, dz = row
                handle.write(
                    f"{symbol:<3s} {x:16.8f} {y:16.8f} {z:16.8f} "
                    f"{dx:16.8f} {dy:16.8f} {dz:16.8f}\n"
                )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract vibrational frequencies and normal modes from a VASP OUTCAR "
            "and generate files for Jmol visualization."
        )
    )

    parser.add_argument(
        "--outcar",
        default="OUTCAR",
        help="Path to OUTCAR (default: OUTCAR)",
    )
    parser.add_argument(
        "--contcar",
        default="CONTCAR",
        help="Path to CONTCAR (default: CONTCAR)",
    )
    parser.add_argument(
        "--frequencies-output",
        default="frequency-values.dat",
        help="Output file for extracted frequencies (default: frequency-values.dat)",
    )
    parser.add_argument(
        "--xyz-output",
        default="vibrational-modes.xyz",
        help="Output XYZ file for Jmol (default: vibrational-modes.xyz)",
    )

    args = parser.parse_args()

    outcar_path = Path(args.outcar)
    contcar_path = Path(args.contcar)
    frequencies_output = Path(args.frequencies_output)
    xyz_output = Path(args.xyz_output)

    species, counts, expanded_symbols = read_contcar_species(contcar_path)
    natoms = len(expanded_symbols)
    modes = parse_outcar_modes(outcar_path, natoms)

    write_frequency_values(frequencies_output, modes)
    write_xyz(xyz_output, modes, expanded_symbols)

    composition = ", ".join(f"{s}:{c}" for s, c in zip(species, counts))
    print(f"Number of atoms  = {natoms}")
    print(f"Composition      = {composition}")
    print(f"Number of modes  = {len(modes)}")
    print(f"Wrote            = {frequencies_output}")
    print(f"Wrote            = {xyz_output}")


if __name__ == "__main__":
    main()