# IR intensities from finite differences

This directory contains scripts and examples to compute **mode-resolved dynamic dipole derivatives** and **finite-difference IR intensities** from VASP vibrational calculations.

The main script is:

- `dyndip_intensities_general_xyz_legacy.sh`

This script is the recommended version in this directory.

## What is computed

For each normal mode, the script evaluates the projection of the finite-difference dipole derivatives onto the normalized vibrational eigenvector.

The script reads the dipole moments printed in the `OUTCAR` for the displaced structures and builds the Cartesian derivatives of the dipole moment with respect to each active degree of freedom. These derivatives are then projected onto each normal mode.

The most complete output includes:

- `dmu_x`
- `dmu_y`
- `dmu_z`
- `|dmu|^2 = dmu_x^2 + dmu_y^2 + dmu_z^2`

In addition, for direct comparison with older scripts, the script also prints the corresponding **legacy component-wise projections**:

- `legacy_x`, `legacy_x^2`
- `legacy_y`, `legacy_y^2`
- `legacy_z`, `legacy_z^2`

This is useful to verify, for example, whether the intensity is dominated by a single dipole component or whether the `x` and `y` contributions are zero or negligible.

## Supported settings

The script is intended for VASP finite-difference vibrational calculations and supports:

- `IDIPOL = 3`
- `IDIPOL = 4`
- `NFREE = 2`
- `NFREE = 4`

For `IDIPOL = 3`, older scripts that use only the `z` dipole component may still be meaningful.  
For `IDIPOL = 4`, the present script is preferred because it uses the **full dipole vector** instead of only one component.

## Main script

### `dyndip_intensities_general_xyz_legacy.sh`

This is the general and recommended script.

Main features:

- does **not** depend on hardcoded chemical species
- reads the number of atoms from `OUTCAR`
- extracts vibrational frequencies and eigenvectors directly from the `OUTCAR`
- reads the **full dipole vector** `(mu_x, mu_y, mu_z)`
- supports both `NFREE = 2` and `NFREE = 4`
- supports both `IDIPOL = 3` and `IDIPOL = 4`
- reads `Selective dynamics` flags from `POSCAR` or `CONTCAR` if present
- prints both the **full vector result** and the **legacy component-wise projections**

## Output

The script prints one line per vibrational mode.

The output columns are:

- `mode`  
  Vibrational mode index

- `freq(cm-1)`  
  Vibrational frequency in cm<sup>-1</sup>

- `dmu_x`, `dmu_y`, `dmu_z`  
  Components of the projected dynamic dipole derivative for that mode

- `|dmu|^2`  
  Total finite-difference IR measure obtained from the full dipole vector:
  
  `|dmu|^2 = dmu_x^2 + dmu_y^2 + dmu_z^2`

- `legacy_x`, `legacy_x^2`  
  Projection and squared projection using only the `x` dipole component

- `legacy_y`, `legacy_y^2`  
  Projection and squared projection using only the `y` dipole component

- `legacy_z`, `legacy_z^2`  
  Projection and squared projection using only the `z` dipole component

At the end, the script also prints a short summary including:

- `NIONS`
- `DOF`
- `NFREE`
- `POTIM`
- `IDIPOL`
- number of parsed dipole entries

## Repository structure

```text
IR_intensities_finite_differences/
├── dyndip_intensities_general_xyz_legacy.sh
├── dyndip_other_versions/
│   ├── dyndip_intensidades
│   ├── dyndip_intensidades2
│   ├── dyndip_intensities4.sh
│   └── dyndip_norm_intensidades_Agustin
├── example1_vasp5.4.4/
│   ├── CONTCAR
│   ├── INCAR
│   ├── KPOINTS
│   ├── OSZICAR
│   ├── OUTCAR
│   └── POSCAR
├── example2_vasp6.3.0/
│   ├── CONTCAR
│   ├── INCAR
│   ├── KPOINTS
│   ├── OSZICAR
│   ├── OUTCAR
│   └── POSCAR
└── example3_vasp6.5.1/
    ├── CONTCAR
    ├── INCAR
    ├── KPOINTS
    ├── OSZICAR
    ├── OUTCAR
    └── POSCAR