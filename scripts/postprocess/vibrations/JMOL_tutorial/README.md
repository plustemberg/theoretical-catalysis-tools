# Jmol tutorial for visualizing vibrational modes

This directory contains a short tutorial on how to use **Jmol** to visualize vibrational modes generated from VASP output.

## Install Jmol

Jmol can be downloaded from the official website:

[Jmol official website](https://jmol.sourceforge.net/)

After downloading the program, unzip the package and open `jmol.jar`.

## Files needed

To visualize the vibrational modes, you should have:

- `vibrational-modes.xyz`  
  Multi-frame XYZ file containing the vibrational modes

- `frequency-values.dat`  
  File listing the vibrational frequencies associated with each normal mode

## How to use Jmol

1. Download and unzip Jmol from the official website.
2. Launch Jmol by opening `jmol.jar`.
3. Open `vibrational-modes.xyz` from within Jmol, or drag and drop the file into the main Jmol window.
4. Go to **Tools → Vibration → Start vibration**.
5. The atoms will begin to move according to the selected vibrational mode.
6. Use the blue arrows in the Jmol window to move forward or backward through the different modes.
7. The mode index shown in Jmol follows the same order as in `frequency-values.dat`.
8. Use the mouse to rotate, move, and zoom the structure interactively.

## Notes

- The frequencies listed in `frequency-values.dat` correspond to the modes shown in Jmol.
- This is a simple visualization workflow intended to inspect normal modes interactively.
- Menu names may vary slightly depending on the Jmol version or operating system.