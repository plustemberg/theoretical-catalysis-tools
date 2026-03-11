# IR intensities from DFPT linear response

This directory contains a Bash-based workflow to extract **infrared intensities** from a VASP **DFPT / linear-response** vibrational calculation.

The present workflow is based on the public script by **David Karhánek** (https://github.com/dakarhanek/VASP-infrared-intensities/blob/master/README.md), adapted here as a practical example together with the corresponding VASP input/output files.

## Physical background

In the DFPT linear-response formalism, infrared intensities can be obtained from the coupling between the **Born effective charge (BEC) tensors** and the vibrational eigenvectors. In practice, the IR activity of each normal mode is related to the change in polarization induced by the atomic displacements associated with that mode.

Within the dipole approximation, the intensity of a normal mode can be expressed in terms of the Born effective charges and the displacement vectors of the corresponding vibrational eigenmode. This is the theoretical basis behind the present workflow.

## Contents

This directory includes:

- `intensity.sh`  
  Bash script that extracts Born effective charge tensors and vibrational eigenvectors from `OUTCAR`, processes them, and computes IR intensities

- `OUTCAR`  
  VASP output file containing the Born effective charge tensors and the mass-weighted vibrational eigenvectors

- `CONTCAR`  
  Final structure

- `POSCAR`, `INCAR`, `OSZICAR`  
  Additional VASP files included for reference

- `born.txt`  
  Extracted Born effective charge tensors

- `eigenvectors.txt`  
  Extracted vibrational eigenvectors and frequencies

- `results.txt`  
  Frequencies and normalized IR intensities

- `exact.res.txt`  
  Frequencies and non-normalized IR intensities

- `statistics.txt`  
  Summary of the number of atoms, vibrations, and matrix operations

- `Dissertation.pdf`  
  Additional theoretical background on DFPT vibrational properties, Born effective charges, and IR intensities

## Workflow

The script reads `OUTCAR` and:

1. extracts the **Born effective charge tensors** into `born.txt`
2. extracts the **mass-weighted vibrational eigenvectors** into `eigenvectors.txt`
3. creates the directory `intensities/`
4. stores the extracted raw files under `intensities/inputs/`
5. computes the IR intensities
6. stores the final output under `intensities/results/`

After execution, the main results are found in:

- `intensities/results/results.txt`
- `intensities/results/exact.res.txt`
- `intensities/results/statistics.txt`

## Requirements

To run this workflow, the following file must be present in the same directory:

- `OUTCAR`

The script also uses standard Unix tools such as:

- `bash`
- `grep`
- `awk`
- `sed`
- `split`
- `bc`

## Recommended VASP settings

Once the structure has been fully relaxed, run a new calculation for DFPT vibrational analysis including:

## IMPORTANT 

1. TESTED with VASP version 5* 
2. vdW-D3 is not implemented in DFPT

```bash
IBRION   = 7
ISIF     = 0
LEPSILON = .TRUE.
NSW      = 1
NWRITE   = 3
ISYM     = 0

