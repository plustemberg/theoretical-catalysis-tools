# ASE NEB Viewer

This script collects all `CONTCAR` files from numbered NEB image folders (`00`, `01`, `02`, ...) and writes them into a single ASE trajectory file, `neb_images.traj`, which can be opened with `ase gui`.

This is useful for inspecting all NEB images as a sequence, instead of opening each `CONTCAR` one by one in VESTA.

## Script name

build_neb_traj.py

## Requirements

 - Python 3

 - ASE (ase)

 - Tkinter (python3-tk) for ase gui

## Installation
```bash
python3 -m pip install --user ase
sudo apt update
sudo apt install python3-tk
```

## Script

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

write('neb_images.traj', images)
print(f"Wrote {len(images)} images to neb_images.traj")
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
python3 build_neb_traj.py
```
if successful, it will create:
```bash
neb_images.traj
```
Then open it with ASE GUI:
```bash
ase gui neb_images.traj
```


