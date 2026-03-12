# IR intensities from finite differences

This directory contains scripts and examples to compute **mode-resolved dynamic dipole derivatives** and **finite-difference IR intensities** from VASP vibrational calculations.

> **Recommended script:** `dyndip_intensities_general_xyz_legacy.sh`

## Main script

### `dyndip_intensities_general_xyz_legacy.sh`

This is the general and recommended workflow in this directory.

It:

- reads vibrational frequencies and eigenvectors from `OUTCAR`
- reads the full dipole vector `(mu_x, mu_y, mu_z)`
- projects the dipole derivatives onto each normal mode
- supports:
  - `IDIPOL = 3`
  - `IDIPOL = 4`
  - `NFREE = 2`
  - `NFREE = 4`
- does not depend on hardcoded chemical species
- uses `POSCAR` or `CONTCAR` to read `Selective dynamics` flags when present

## What is computed

For each normal mode, the script computes:

- `dmu_x`
- `dmu_y`
- `dmu_z`
- `|dmu|^2 = dmu_x^2 + dmu_y^2 + dmu_z^2`

It also prints **legacy component-wise projections** for direct comparison with older scripts:

- `legacy_x`, `legacy_x^2`
- `legacy_y`, `legacy_y^2`
- `legacy_z`, `legacy_z^2`

These extra columns are useful to verify whether the intensity is dominated by a single dipole component, or whether the `x` and `y` contributions are zero or negligible.

## Output

The script prints one line per vibrational mode with:

- mode index
- frequency in `cm^-1`
- projected dipole components: `dmu_x`, `dmu_y`, `dmu_z`
- total vectorial intensity measure: `|dmu|^2`
- legacy component-wise projections and squared values for `x`, `y`, and `z`

At the end, a short summary is printed with:

- `NIONS`
- `DOF`
- `NFREE`
- `POTIM`
- `IDIPOL`
- number of parsed dipole entries

## Directory structure

```text
IR_intensities_finite_differences/
├── dyndip_intensities_general_xyz_legacy.sh
├── dyndip_other_versions/
│   ├── dyndip_intensidades
│   ├── dyndip_intensidades2
│   ├── dyndip_intensities4.sh
│   └── dyndip_norm_intensidades_Agustin
├── example1_vasp5.4.4/
├── example2_vasp6.3.0/
└── example3_vasp6.5.1/