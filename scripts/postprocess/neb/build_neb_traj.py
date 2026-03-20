from pathlib import Path
from ase.io import read, write

images = []

for d in sorted(Path('.').glob('[0-9][0-9]')):
    f = d / 'CONTCAR'
    if f.exists():
        images.append(read(f))

if not images:
    raise SystemExit("No encontré archivos 00/CONTCAR, 01/CONTCAR, ...")

write('neb_images.traj', images)
print(f"Escribí {len(images)} imágenes en neb_images.traj")
