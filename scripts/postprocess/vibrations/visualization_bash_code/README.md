# Vibrational mode visualization with Jmol from VASP output

This directory contains a simple Bash-based workflow to extract vibrational frequencies and normal-mode displacements from a VASP frequency calculation and generate an XYZ file that can be visualized with Jmol.

The present example corresponds to **8CO adsorbed on MgO**.

## Contents

This directory includes:

- `vibrational-modes-jmol.sh`  
  Bash script that extracts the vibrational information from the VASP output files

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

## Current scope

This example is currently tailored to a **CO/MgO** system and assumes the presence of the following species in `CONTCAR`:

- Mg
- O
- C

Therefore, the script is not yet fully general and should be considered as a working example for this specific type of system.

## Requirements

To run this workflow, the following files must be present in the same directory:

- `OUTCAR`
- `CONTCAR`

To visualize the resulting XYZ file, **Jmol** must be installed separately on your system.

## How to run

Recommended:

```bash
chmod +x vibrational-modes-jmol.sh
./vibrational-modes-jmol.sh

Alternative: 

bash vibrational-modes-jmol.sh