# `make_adsorption_montage.py`

Create a PNG montage of adsorption structures from recursively generated top-view images and compute adsorption energies automatically from `OUTCAR`/`OSZICAR`.

This script is designed to work **after** running the recursive OVITO-based rendering workflow. It scans subdirectories, locates the individual **top-view PNG** for each calculation, extracts the **final total energy** from `OSZICAR` or `OUTCAR`, computes:

`Eads = Efinal - Ereference`

and builds a single summary image containing all structures.

---

## What this script does

For every matching calculation directory, the script:

1. finds a **top-view image** (`relax_view_xy.png` by default, or another matching `*_view_xy.png`)
2. reads the **final energy** from:
   - `OSZICAR` first, if available
   - otherwise `OUTCAR`
3. computes the adsorption energy:
   - `Eads = Efinal - Ereference`
4. creates a **montage PNG** with:
   - the directory label at the top
   - the structure image in the center
   - the adsorption energy at the bottom
5. writes a **CSV summary** with all detected entries and energies

---

## Typical use case

You already generated one top-view image per calculation, for example:

- `1/res1/relax_view_xy.png`
- `2/res1/relax_view_xy.png`
- `3/res1/relax_view_xy.png`
- ...

and each directory also contains `OUTCAR` and/or `OSZICAR`.

Then this script builds a global adsorption map such as:

- **5 columns per row**
- as many rows as needed
- one structure per panel
- one `Eads` value per panel

---

## Requirements

Python 3 with:

- `Pillow`
- `numpy`

Install with:

```bash
pip install pillow numpy
```

---

## Basic usage

From the root directory containing all subfolders:

```bash
python make_adsorption_montage.py . --reference -1234.56789
```

This will:

- recursively search inside `.`
- compute adsorption energies using `-1234.56789 eV` as the reference energy
- create:
  - `adsorption_montage.png`
  - `adsorption_montage.csv`

---

## Energy expression

The script uses:

```text
Eads = Efinal - Ereference
```

where:

- `Efinal` = last energy found in `OSZICAR` or `OUTCAR`
- `Ereference` = user-provided reference energy via `--reference`

### Energy source priority

The script tries in this order:

1. `OSZICAR`
2. `OUTCAR`

This is useful because `OSZICAR` is usually faster and simpler to parse, while `OUTCAR` provides a fallback if `OSZICAR` is missing.

---

## Default detected image

By default the script looks for a top-view PNG in this order:

1. `relax_view_xy.png`
2. the newest file matching `*_view_xy.png`

You can also force a specific image name.

Example:

```bash
python make_adsorption_montage.py . --reference -1234.56789 --image-name top.png
```

---

## Output files

By default the script writes:

- `adsorption_montage.png`
- `adsorption_montage.csv`

You can customize them:

```bash
python make_adsorption_montage.py . --reference -1234.56789 -o my_grid.png --csv my_grid.csv
```

---

## Layout options

### Number of columns

Default: **5 columns**

Example with 4 columns:

```bash
python make_adsorption_montage.py . --reference -1234.56789 --columns 4
```

The number of rows is adjusted automatically.

---

## Label options

### Label mode

The label shown above each structure can be:

- relative path (default)
- basename only

#### Default behavior

Examples:

- `1/res1`
- `10/res1`
- `neb/neb1/07`

#### Basename only

Example:

```bash
python make_adsorption_montage.py . --reference -1234.56789 --label-mode basename
```

This would show only:

- `res1`
- `07`
- etc.

---

## Sorting modes

### 1. Natural sorting (default)

The script now uses **natural sorting** by default, so directories are ordered like:

```text
1, 2, 3, ..., 9, 10
```

instead of:

```text
1, 10, 2, 3, ...
```

Usage:

```bash
python make_adsorption_montage.py . --reference -1234.56789 --sort natural
```

or simply:

```bash
python make_adsorption_montage.py . --reference -1234.56789
```

### 2. Energy sorting

You can sort the panels by adsorption energy from **most negative** to **most positive**:

```bash
python make_adsorption_montage.py . --reference -1234.56789 --sort energy
```

This is useful when you want the most stable adsorption configurations to appear first.

---

## Include / exclude filters

The script supports several ways to restrict which directories are used.

### Exclude directories whose components start with a prefix

Example: exclude all paths containing components beginning with `neb`

```bash
python make_adsorption_montage.py . --reference -1234.56789 --exclude-prefix neb
```

### Include only directories whose components start with a prefix

Example: include only paths containing components beginning with `res`

```bash
python make_adsorption_montage.py . --reference -1234.56789 --include-prefix res
```

### Select only specific folders or paths

Example:

```bash
python make_adsorption_montage.py . --reference -1234.56789 --only 6/res1 --only 7/res1 --only 10/res1
```

`--only` accepts:

- exact relative paths
- directory basenames
- path prefixes

### Include by glob pattern

Example:

```bash
python make_adsorption_montage.py . --reference -1234.56789 --include-glob '6/*' --include-glob '7/*'
```

### Exclude by glob pattern

Example:

```bash
python make_adsorption_montage.py . --reference -1234.56789 --exclude-glob 'neb*' --exclude-glob '*/old/*'
```

### Combined filtering example

```bash
python make_adsorption_montage.py . --reference -1234.56789 --sort energy --include-prefix res --exclude-prefix neb
```

---

## Common examples

### 1. Basic montage from the current directory

```bash
python make_adsorption_montage.py . --reference -500.000000
```

### 2. Sort by adsorption energy

```bash
python make_adsorption_montage.py . --reference -500.000000 --sort energy
```

### 3. Use basename labels only

```bash
python make_adsorption_montage.py . --reference -500.000000 --label-mode basename
```

### 4. Exclude NEB-related folders

```bash
python make_adsorption_montage.py . --reference -500.000000 --exclude-prefix neb
```

### 5. Use only selected results

```bash
python make_adsorption_montage.py . --reference -500.000000 --only 1/res1 --only 4/res1 --only 8/res1
```

### 6. Force a specific image filename

```bash
python make_adsorption_montage.py . --reference -500.000000 --image-name my_top_view.png
```

### 7. Change output names

```bash
python make_adsorption_montage.py . --reference -500.000000 -o CH4_adsorption_grid.png --csv CH4_adsorption_grid.csv
```

### 8. Change the number of columns

```bash
python make_adsorption_montage.py . --reference -500.000000 --columns 6
```

---

## CSV output

The CSV file contains a machine-readable summary of the montage.

Typical fields include:

- relative directory
- absolute directory
- image used
- energy source used (`OSZICAR` or `OUTCAR`)
- final energy
- reference energy
- adsorption energy

This is useful for:

- sorting externally
- plotting energies later
- checking missing or failed entries
- building tables for reports or manuscripts

---

## Recommended workflow

A typical workflow is:

### Step 1: Generate structure views recursively

Use your OVITO-based script first, for example:

```bash
python outcar_relax_to_ovito_real.py . --recursive
```

This generates `relax_view_xy.png` in each calculation folder.

### Step 2: Build the adsorption montage

```bash
python make_adsorption_montage.py . --reference -500.000000 --sort energy
```

---

## Notes and assumptions

- The script assumes that each calculation folder contains a valid **top-view image** and at least one valid energy source (`OSZICAR` or `OUTCAR`).
- If both files are missing or no final energy can be parsed, that folder is skipped.
- If no suitable image is found, that folder is skipped.
- For recursive operation, the input path must be a **directory**.
- The script does **not** regenerate images; it only assembles already existing PNG files.

---

## Troubleshooting

### Problem: a folder is missing from the montage

Check:

1. Does the directory contain a top-view PNG?
2. Does it contain `OSZICAR` or `OUTCAR`?
3. Is it being filtered out by `--exclude-prefix`, `--exclude-glob`, etc.?
4. Are you pointing the script to the correct root directory?

### Problem: folder `10` appears between `1` and `2`

Use:

```bash
--sort natural
```

This is now the default behavior.

### Problem: I want the most stable structures first

Use:

```bash
--sort energy
```

This sorts by `Eads` from most negative to most positive.

### Problem: recursive search does not work

Use a directory as input, not a file:

Correct:

```bash
python make_adsorption_montage.py . --reference -500.000000
```

Incorrect:

```bash
python make_adsorption_montage.py OUTCAR --reference -500.000000
```

---

## Suggested use in adsorption studies

This script is especially useful when comparing many adsorption configurations such as:

- different initial placements
- multiple adsorption sites
- different spin states
- several relaxation outcomes
- different intermediates or fragments

The final montage gives a quick visual summary of:

- structure
- relative stability
- directory identity

which is convenient for screening and reporting.

---

## Example command for a typical project

```bash
python make_adsorption_montage.py . \
  --reference -500.000000 \
  --sort energy \
  --exclude-prefix neb \
  --columns 5 \
  -o adsorption_montage.png \
  --csv adsorption_montage.csv
```

---

## Script name

Main script:

```text
make_adsorption_montage.py
```

---

## Author notes

This script was designed to complement an OVITO-based recursive rendering workflow for VASP relaxations and adsorption calculations, allowing rapid visual comparison of many final structures together with their adsorption energies.
