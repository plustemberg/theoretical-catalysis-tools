# ASE NEB Viewer

This script collects all `CONTCAR` files from numbered NEB image folders (`00`, `01`, `02`, ...) and writes them into a single `extended XYZ` trajectory file, `neb_images.extxyz`, which can be opened in OVITO.

This is useful for visualizing all NEB images as a sequence in OVITO, instead of opening each image separately.

## Script name
```bash
build_neb_extxyz.py
```
## Requirements

 - Python 3

 - ASE (ase)

 - OVITO installed on your system

## Installation
```bash
python3 -m pip install --user ase
```
Install OVITO as appropriate for your operating system.

## Script

Save the following as build_neb_extxyz.py:

```bash
from pathlib import Path
from ase.io import read, write

images = []

for d in sorted(Path('.').glob('[0-9][0-9]')):
    f = d / 'CONTCAR'
    if f.exists():
        images.append(read(f))

if not images:
    raise SystemExit("No CONTCAR files found in folders 00, 01, 02, ...")

write('neb_images.extxyz', images)
print(f"Wrote {len(images)} images to neb_images.extxyz")
```
## How to use

Go to the NEB calculation directory, for example:
```bash
cd /path/to/your/neb_calculation
```
The directory should contain folders like:
```bash
00  01  02  03  04  05  06  07 ...
```
Run the script:
```bash
python3  build_neb_extxyz.py
```
if successful, it will create:
```bash
neb_images.extxyz
```
### Then open it with OVITO:

Open OVITO and load the generated file:
```bash
neb_images.extxyz
```
OVITO will interpret the file as a trajectory with multiple frames, so you can move through the NEB images using the timeline controls.

