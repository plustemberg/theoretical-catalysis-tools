# Occupation matrix control in VASP

This repository includes input files to constrain and initialize selected DFT+U occupations in VASP using the occupation-matrix-control patch. This functionality does not directly impose the final electron distribution; rather, it biases the occupations used in the DFT+U correction and is therefore mainly useful to (i) initialize a specific electronic configuration or (ii) localize a given electron/polaron on a chosen site before letting the system relax further

Two input routes exist in the patched code: OCCDIRX, where selected occupation-matrix elements are written directly in the INCAR, and OCCEXT, where the occupations are read from an external file named OCCMATRIX. In practice, the second route is usually more convenient when the local crystal field is not aligned with the Cartesian axes, when many d/f electrons are involved, or when off-diagonal matrix elements matter. In this repository we use the OCCMATRIX approach

## Recommended workflow

1. Start from a standard DFT+U setup and set LDAUPRINT = 2 in the INCAR to print the occupation matrices in the OUTCAR.

2. Inspect the printed matrices and identify the occupation pattern you want to initialize.

3. Create an OCCMATRIX file with the occupations of the atoms you want to constrain.

4. Add OCCEXT = 1 to the INCAR and run VASP with the patched executable.

5. After the target localization/distortion is obtained, restart the calculation without OCCEXT = 1 so the system can relax without the external occupation bias.

This two-step strategy is important because occupation control is best used to guide the initial localization/distortion; after that, the calculation should be restarted without the constraint and the final electronic state must be checked again, typically using LDAUPRINT = 2

## Format of OCCMATRIX

The OCCMATRIX file follows the same general structure as the occupation-matrix output printed by VASP when LDAUPRINT = 2 is enabled. The first line is the number of atoms whose occupations will be specified. Then, for each atom, a block is provided with:

* atom index in the POSCAR

* angular momentum L (0=s, 1=p, 2=d, 3=f)

* spin flag (2 for spin-polarized, 1 for non-spin-polarized)

This is followed by a label line for the spin component, the spin-up matrix, and, if spin-polarized, a second label plus the spin-down matrix. Blank lines separate consecutive atomic blocks.

## Running on MareNostrum 5 (MN5)

In our MN5 setup, the patched occupation-matrix version is run with the following module stack and executable: 

```bash
module purge
module load impi/2021.9.0 oneapi/2023.1 intel/2023.1 mkl/2022.1 ucx vasp/5.4.4-Occupation_matrix_v1.4
srun /apps/GPP/VASP/5.4.4-Occupation_matrix_v1.4/INTEL/IMPI/bin/vasp_std
```
The reference repository provides patches for VASP 5.4.4, and its documented versions indicate explicit support for VASP 5.4.4 and an additional spin-orbit-enabled variant.

## Files included in this repository

Typical files needed for this workflow are:

* INCAR_initial

* INCAR_with_occ_matrix

* magnetization_after.txt

* magnetization_before.txt

* OCCMATRIX

No OUTCAR examples are included in the repository. Once LDAUPRINT = 2 is enabled, VASP prints the occupation matrices explicitly in the OUTCAR, which makes these files unnecessarily large for version control and examples

## Practical note

A good initial strategy is to first run with a relatively robust setup that achieves the intended localization using OCCEXT = 1, and only afterwards restart from the converged geometry/wavefunction without occupation forcing and with the final production settings. That is the logic followed in the notes you shared and is also consistent with the usage advice in the reference implementation.