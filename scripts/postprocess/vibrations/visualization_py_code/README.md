# Vibrational mode visualization with Jmol from VASP output

This directory contains a simple Python-based workflow to extract vibrational frequencies and normal-mode displacements from a VASP frequency calculation and generate an XYZ file that can be visualized with Jmol.

Unlike the original Bash-based example, this implementation is intended to be **general** and does **not depend on a specific chemical system**, as the atomic species and their multiplicities are read directly from `CONTCAR`.

## Contents

This directory includes:

- `vibrational-modes-jmol.py`  
  Python script that extracts the vibrational information from the VASP output files

- `OUTCAR`  
  VASP output file containing the vibrational frequencies and eigenvectors

- `CONTCAR`  
  Final structure used to identify the atomic composition

- `POSCAR`, `INCAR`, `KPOINTS`  
  Additional VASP input files included for reference

- `frequency-values.dat`  
  File containing the vibrational frequencies extracted from `OUTCAR`

- `vibrational-modes.xyz`  
  Multi-frame XYZ file containing the vibrational modes for visualization in Jmol

## Purpose

The script reads the vibrational modes from `OUTCAR`, reconstructs the atomic labels from `CONTCAR`, and writes an XYZ trajectory-like file that can be opened in Jmol as an animation of the normal modes.

## Scope

This Python implementation is designed to be **system-independent** within the standard VASP vibrational output format. In particular, it does not assume a fixed set of atomic species such as Mg, O, and C, but instead reads the element symbols and atom counts directly from `CONTCAR`.

The script has been tested on different systems, but users should still proceed with caution and always verify that the generated frequencies and vibrational modes are consistent with the original VASP output.

## Requirements

To run this workflow, the following files must be present in the same directory:

- `OUTCAR`
- `CONTCAR`

A standard Python 3 installation is required. No external Python packages are needed.

To visualize the resulting XYZ file, **Jmol** must be installed separately on your system.

## How to run

Recommended:

```bash
python3 vibrational-modes-jmol.py