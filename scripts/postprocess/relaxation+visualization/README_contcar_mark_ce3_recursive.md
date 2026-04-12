# README — `contcar_mark_ce3_recursive.py`

## What this script does

`contcar_mark_ce3_recursive.py` searches **recursively** for folders that contain both a `CONTCAR` and an `OUTCAR`. In each matching folder, it:

1. reads the **last** `magnetization (x)` section from the `OUTCAR`,
2. takes the **`f`** column,
3. identifies the atoms whose value satisfies `|f| > threshold`,
4. restricts that selection to the **initial Ce block** in the `CONTCAR`,
5. and rewrites the **species** and **atom-count** lines so that the detected `Ce3+` atoms are labeled as `La`.

The goal is to generate a `CONTCAR` where the `Ce3+` atoms are made **explicit visually** without changing the atomic coordinates.

---

## General idea of the procedure

The script assumes the standard VASP ordering in the `CONTCAR`:

- line 6 contains the species names,
- line 7 contains the number of atoms of each species,
- and the coordinates are grouped by species in the same order.

For example, if the `CONTCAR` contains:

```text
Ce O Ni
32 64 6
```

and the indices with `|f| > 0.8` in the last `magnetization (x)` block of the `OUTCAR` are:

```text
3 10 16
```

then the script transforms:

```text
Ce O Ni
32 64 6
```

into:

```text
Ce La Ce La Ce La Ce O Ni
2 1 6 1 5 1 16 64 6
```

That is, each detected `Ce3+` atom is split out as an individual `La` block within the original Ce block.

---

## What it modifies and what it does not modify

### Modified

Only the following lines of the `CONTCAR` are changed:

- **line 6**: chemical species
- **line 7**: number of atoms per species

### Not modified

- atomic coordinates
- scaling factor
- lattice vectors
- `Selective dynamics` mode
- atomic positions
- the `OUTCAR`

---

## Important assumptions

The current version works correctly if the following conditions are satisfied:

1. The **first species** in the `CONTCAR` is `Ce`.
2. The number of Ce atoms is the **first value** on the atom-count line.
3. Atoms are ordered by species blocks, as in a standard VASP `CONTCAR/POSCAR`.
4. The `magnetization (x)` section exists in the `OUTCAR`.
5. The last column of that table corresponds to the **`f`** value.

### Valid examples

```text
Ce O Ni
32 64 6
```

```text
Ce O Ni O C H
32 64 6 4 1 2
```

```text
Ce O O1Ni C H
32 64 6 2 2 1
```

As long as `Ce` remains the **first species**, the script can act on that first block.

### Example not supported by this version

```text
O Ce Ni
64 32 6
```

In that case, the script will fail, because it expects the initial block to correspond to `Ce`.

---

## What happens if atoms with `|f| > threshold` are found outside the Ce block

The script may detect indices with high magnetization that lie **outside** the initial Ce block. In that case, it:

- reports them on screen as a warning,
- but **does not label them as `La`**, 
- because it only transforms indices that belong to the Ce block.

This avoids incorrectly relabeling other species.

---

## Expected input files

By default, in each folder the script looks for:

- `CONTCAR`
- `OUTCAR`

It only processes folders where **both files** exist.

---

## Output file

By default, the script **does not overwrite** the original `CONTCAR`. Instead, it creates:

```text
CONTCAR_Ce3
```

If desired, the original file can be overwritten with the `--in-place` option.

---

## Basic usage

### Search from the current directory

```bash
python contcar_mark_ce3_recursive.py .
```

This scans the current directory and all subdirectories, and processes every folder containing both `CONTCAR` and `OUTCAR`.

---

## Available options

### `root`

Root directory from which the recursive search starts.

```bash
python contcar_mark_ce3_recursive.py /path/to/project
```

---

### `--contcar-name`

Allows changing the name of the `CONTCAR` file to search for.

```bash
python contcar_mark_ce3_recursive.py . --contcar-name CONTCAR.relax
```

---

### `--outcar-name`

Allows changing the name of the `OUTCAR` file to search for.

```bash
python contcar_mark_ce3_recursive.py . --outcar-name OUTCAR.relax
```

---

### `-o`, `--output-name`

Allows defining the output filename in each folder.

```bash
python contcar_mark_ce3_recursive.py . -o CONTCAR_marked
```

By default it uses:

```text
CONTCAR_Ce3
```

---

### `--in-place`

Overwrites the original `CONTCAR` instead of creating a new file.

```bash
python contcar_mark_ce3_recursive.py . --in-place
```

Use this option with care.

---

### `-t`, `--threshold`

Sets the threshold applied to `|f|` in the last `magnetization (x)` block.

Default value:

```text
0.8
```

Example:

```bash
python contcar_mark_ce3_recursive.py . --threshold 0.85
```

The applied criterion is:

```text
|f| > threshold
```

---

### `--dry-run`

Shows what the script would do, but **does not write any files**.

```bash
python contcar_mark_ce3_recursive.py . --dry-run
```

This is the best option to verify the result before modifying anything.

---

### `-q`, `--quiet`

Reduces the amount of information printed to screen.

```bash
python contcar_mark_ce3_recursive.py . --quiet
```

---

## Usage examples

### 1. Check which folders would be processed, without writing anything

```bash
python contcar_mark_ce3_recursive.py . --dry-run
```

### 2. Process everything recursively and save as `CONTCAR_Ce3`

```bash
python contcar_mark_ce3_recursive.py .
```

### 3. Overwrite all `CONTCAR` files

```bash
python contcar_mark_ce3_recursive.py . --in-place
```

### 4. Use different filenames

```bash
python contcar_mark_ce3_recursive.py . --contcar-name POSCAR --outcar-name OUTCAR.relax
```

### 5. Change the `Ce3+` identification threshold

```bash
python contcar_mark_ce3_recursive.py . -t 1.0
```

---

## Screen output

In normal mode, for each folder the script prints something like:

```text
[DIR] /path/to/folder
  Ce3+ detected (|f| > 0.8): [3, 10, 16]
  Ce3+ inside the Ce block : [3, 10, 16]
  New line 6: Ce  La  Ce  La  Ce  La  Ce  O  Ni
  New line 7: 2  1  6  1  5  1  16  64  6
  [OK] /path/to/folder/CONTCAR -> /path/to/folder/CONTCAR_Ce3
```

If it finds indices outside the Ce block, it adds a warning such as:

```text
Warning: there are indices > nCe that are not labeled as La: [...]
```

At the end, it prints a global summary:

```text
Summary: X folder(s) processed successfully, Y with errors.
```

---

## Limitations of this version

1. It **requires `Ce` to be the first species** in the `CONTCAR`.
2. It does **not chemically verify** whether an atom is truly `Ce3+`; it only applies the magnetization criterion `|f| > threshold`.
3. `La` is used only as a **visual identification label**.
4. The generated file **should not be used directly to run VASP** unless the rest of the input files (`POTCAR`, etc.) are made consistent with that species change.

---

## Recommended workflow

Always test first with:

```bash
python contcar_mark_ce3_recursive.py . --dry-run
```

Then check that:

- the detected indices are the expected ones,
- the new species line makes sense,
- the new atom-count line matches the intended partition of the Ce block.

After that, run it in normal mode.

---

## Requirements

- Python 3
- No external libraries required

---

## Script name

Main file:

```text
contcar_mark_ce3_recursive.py
```
