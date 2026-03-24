#!/usr/bin/env python3
"""Utilities for parsing and post-processing VASP DOSCAR/OUTCAR/CONTCAR files.

Designed for practical DOS workflows in catalysis projects:
- robust header detection
- automatic handling of ISPIN = 1 / 2
- support for common LORBIT=11 projected-DOS layouts
- atom selection by indices or element
- lightweight streaming of large DOSCAR files
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple
import math
import re


@dataclass
class DOSMetadata:
    doscar: Path
    natoms: int
    nedos: int
    efermi: float
    total_ncols: int
    proj_ncols: Optional[int]
    ispin: Optional[int] = None
    lorbit: Optional[int] = None
    species: Optional[List[str]] = None
    counts: Optional[List[int]] = None
    z_cart: Optional[List[float]] = None

    @property
    def energy_column_count(self) -> int:
        return 1


def _read_first_lines(path: Path, n: int) -> List[str]:
    lines = []
    with path.open("r") as fh:
        for _ in range(n):
            try:
                lines.append(next(fh))
            except StopIteration:
                break
    return lines


_FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?")


def parse_outcar(path: str | Path = "OUTCAR") -> Dict[str, Optional[float]]:
    path = Path(path)
    data: Dict[str, Optional[float]] = {
        "ISPIN": None,
        "NEDOS": None,
        "LORBIT": None,
        "EFERMI": None,
    }
    if not path.exists():
        return data

    with path.open("r", errors="replace") as fh:
        for line in fh:
            if "ISPIN" in line and "=" in line:
                m = re.search(r"ISPIN\s*=\s*(\d+)", line)
                if m:
                    data["ISPIN"] = int(m.group(1))
            if "NEDOS" in line and "=" in line:
                m = re.search(r"NEDOS\s*=\s*(\d+)", line)
                if m:
                    data["NEDOS"] = int(m.group(1))
            if "LORBIT" in line and "=" in line:
                m = re.search(r"LORBIT\s*=\s*(-?\d+)", line)
                if m:
                    data["LORBIT"] = int(m.group(1))
            if "E-fermi" in line:
                m = re.search(r"E-fermi\s*:\s*([-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?)", line)
                if m:
                    data["EFERMI"] = float(m.group(1))
    return data


def parse_contcar(path: str | Path = "CONTCAR") -> Dict[str, Optional[List[float]]]:
    path = Path(path)
    info: Dict[str, Optional[List[float]]] = {
        "species": None,
        "counts": None,
        "z_cart": None,
    }
    if not path.exists():
        return info

    with path.open("r", errors="replace") as fh:
        lines = [next(fh) for _ in range(9)]
        species = lines[5].split()
        counts = [int(x) for x in lines[6].split()]
        natoms = sum(counts)
        scale = float(lines[1].split()[0])
        lattice = []
        for i in range(2, 5):
            lattice.append([float(x) for x in lines[i].split()[:3]])

        coord_mode_line = lines[7].strip().lower()
        selective = False
        if coord_mode_line.startswith("s"):
            selective = True
            coord_mode = lines[8].strip().lower()
        else:
            coord_mode = coord_mode_line

        # Load remaining coordinate lines directly from file to avoid assumptions.
    with path.open("r", errors="replace") as fh:
        all_lines = fh.readlines()

    coord_start = 9 if selective else 8
    coords = []
    for line in all_lines[coord_start:coord_start + natoms]:
        parts = line.split()
        if len(parts) < 3:
            continue
        coords.append([float(parts[0]), float(parts[1]), float(parts[2])])

    if len(coords) != natoms:
        raise ValueError(f"Expected {natoms} atomic coordinates in {path}, found {len(coords)}.")

    # Cartesian z values are useful for slab/layer grouping.
    if coord_mode.startswith("d"):
        # z_cart = r_z dot c-vector contributions.
        cvec = lattice[2]
        z_cart = [(c[0] * lattice[0][2] + c[1] * lattice[1][2] + c[2] * cvec[2]) * scale for c in coords]
    else:
        z_cart = [c[2] * scale for c in coords]

    info["species"] = species
    info["counts"] = counts
    info["z_cart"] = z_cart
    return info


def read_metadata(
    doscar: str | Path = "DOSCAR",
    outcar: str | Path = "OUTCAR",
    contcar: str | Path = "CONTCAR",
) -> DOSMetadata:
    doscar = Path(doscar)
    with doscar.open("r", errors="replace") as fh:
        line1 = next(fh).split()
        natoms = int(line1[0])
        for _ in range(4):
            next(fh)
        line6 = next(fh).split()
        if len(line6) < 4:
            raise ValueError("Invalid DOSCAR header: line 6 has fewer than 4 columns.")
        nedos = int(round(float(line6[2])))
        efermi = float(line6[3])
        total_first = next(fh).split()
        total_ncols = len(total_first)
        # Skip rest of total block.
        for _ in range(nedos - 1):
            next(fh)
        proj_header = None
        proj_first = None
        try:
            proj_header = next(fh)
            proj_first = next(fh).split()
            proj_ncols = len(proj_first)
        except StopIteration:
            proj_ncols = None

    out_info = parse_outcar(outcar)
    cont_info = parse_contcar(contcar)
    return DOSMetadata(
        doscar=doscar,
        natoms=natoms,
        nedos=nedos,
        efermi=efermi,
        total_ncols=total_ncols,
        proj_ncols=proj_ncols,
        ispin=int(out_info["ISPIN"]) if out_info["ISPIN"] is not None else None,
        lorbit=int(out_info["LORBIT"]) if out_info["LORBIT"] is not None else None,
        species=cont_info["species"],
        counts=cont_info["counts"],
        z_cart=cont_info["z_cart"],
    )


def projected_labels(ncols: int, ispin: Optional[int]) -> List[str]:
    """Return column labels excluding energy for common DOSCAR projected layouts."""
    n = ncols - 1
    if n <= 0:
        return []

    # Prefer ISPIN when available.
    if ispin == 1:
        if n == 1:
            return ["s"]
        if n == 3:
            return ["s", "p", "d"]
        if n == 4:
            return ["s", "p", "d", "f"]
        if n == 9:
            return ["s", "py", "pz", "px", "dxy", "dyz", "dz2", "dxz", "dx2-y2"]
        if n == 16:
            return [
                "s", "py", "pz", "px", "dxy", "dyz", "dz2", "dxz", "dx2-y2",
                "fy(3x2-y2)", "fxyz", "fyz2", "fz3", "fxz2", "fz(x2-y2)", "fx(x2-3y2)"
            ]
    if ispin == 2:
        if n == 2:
            return ["s_up", "s_down"]
        if n == 6:
            return ["s_up", "s_down", "p_up", "p_down", "d_up", "d_down"]
        if n == 8:
            return ["s_up", "s_down", "p_up", "p_down", "d_up", "d_down", "f_up", "f_down"]
        if n == 18:
            base = ["s", "py", "pz", "px", "dxy", "dyz", "dz2", "dxz", "dx2-y2"]
            return [f"{x}_{spin}" for x in base for spin in ("up", "down")]
        if n == 32:
            base = [
                "s", "py", "pz", "px", "dxy", "dyz", "dz2", "dxz", "dx2-y2",
                "fy(3x2-y2)", "fxyz", "fyz2", "fz3", "fxz2", "fz(x2-y2)", "fx(x2-3y2)"
            ]
            return [f"{x}_{spin}" for x in base for spin in ("up", "down")]

    # Fallback guesses from number of columns.
    if n == 9:
        return ["s", "py", "pz", "px", "dxy", "dyz", "dz2", "dxz", "dx2-y2"]
    if n == 10:
        return [f"col{i}" for i in range(1, n + 1)]
    return [f"col{i}" for i in range(1, n + 1)]


def total_labels(ncols: int, ispin: Optional[int]) -> List[str]:
    n = ncols - 1
    if ispin == 2 and n == 4:
        return ["dos_up", "dos_down", "int_up", "int_down"]
    if n == 2:
        return ["dos", "int_dos"]
    return [f"col{i}" for i in range(1, n + 1)]


def iter_total_dos(doscar: str | Path = "DOSCAR") -> Iterator[List[float]]:
    meta = read_metadata(doscar)
    with Path(doscar).open("r", errors="replace") as fh:
        for _ in range(6):
            next(fh)
        for _ in range(meta.nedos):
            yield [float(x) for x in next(fh).split()]


def iter_projected_blocks(doscar: str | Path = "DOSCAR") -> Iterator[Tuple[int, List[List[float]]]]:
    meta = read_metadata(doscar)
    with Path(doscar).open("r", errors="replace") as fh:
        for _ in range(6 + meta.nedos):
            next(fh)
        for atom in range(1, meta.natoms + 1):
            next(fh)  # repeated block header
            block = []
            for _ in range(meta.nedos):
                block.append([float(x) for x in next(fh).split()])
            yield atom, block


def read_total_dos(doscar: str | Path = "DOSCAR") -> Tuple[List[float], List[str], List[List[float]], DOSMetadata]:
    meta = read_metadata(doscar)
    labels = total_labels(meta.total_ncols, meta.ispin)
    energies = []
    cols = [[] for _ in labels]
    for row in iter_total_dos(doscar):
        energies.append(row[0] - meta.efermi)
        for i, value in enumerate(row[1:]):
            cols[i].append(value)
    return energies, labels, cols, meta


def read_projected_atoms(
    atoms: Sequence[int],
    doscar: str | Path = "DOSCAR",
    outcar: str | Path = "OUTCAR",
    contcar: str | Path = "CONTCAR",
) -> Tuple[List[float], List[str], Dict[int, List[List[float]]], DOSMetadata]:
    atoms_set = set(atoms)
    meta = read_metadata(doscar, outcar, contcar)
    if meta.proj_ncols is None:
        raise ValueError("This DOSCAR does not contain projected atomic DOS blocks.")
    labels = projected_labels(meta.proj_ncols, meta.ispin)
    data: Dict[int, List[List[float]]] = {atom: [list() for _ in labels] for atom in atoms}
    energies: List[float] = []

    with Path(doscar).open("r", errors="replace") as fh:
        for _ in range(6 + meta.nedos):
            next(fh)
        for atom in range(1, meta.natoms + 1):
            next(fh)  # block header
            keep = atom in atoms_set
            for i in range(meta.nedos):
                row = [float(x) for x in next(fh).split()]
                if keep:
                    if atom == atoms[0]:
                        if len(energies) < meta.nedos:
                            energies.append(row[0] - meta.efermi)
                    for j, value in enumerate(row[1:]):
                        data[atom][j].append(value)
    return energies, labels, data, meta


def atom_species_map(meta: DOSMetadata) -> Dict[int, str]:
    if not meta.species or not meta.counts:
        return {}
    mapping: Dict[int, str] = {}
    idx = 1
    for sp, count in zip(meta.species, meta.counts):
        for _ in range(count):
            mapping[idx] = sp
            idx += 1
    return mapping


def parse_atom_selection(selection: str, meta: DOSMetadata) -> List[int]:
    """Parse selections such as '1,2,5-8' or 'Mg,O' or mixed strings."""
    if not selection:
        raise ValueError("Empty atom selection.")
    species_map = atom_species_map(meta)
    selected: List[int] = []
    for token in [t.strip() for t in selection.split(",") if t.strip()]:
        if re.fullmatch(r"\d+-\d+", token):
            a, b = [int(x) for x in token.split("-")]
            if a > b:
                a, b = b, a
            selected.extend(range(a, b + 1))
        elif re.fullmatch(r"\d+", token):
            selected.append(int(token))
        else:
            matching = [idx for idx, sp in species_map.items() if sp.lower() == token.lower()]
            if not matching:
                raise ValueError(f"Selection token '{token}' is neither an atom index/range nor an element present in CONTCAR.")
            selected.extend(matching)
    selected = sorted(set(selected))
    if not selected:
        raise ValueError("No atoms selected.")
    for atom in selected:
        if atom < 1 or atom > meta.natoms:
            raise ValueError(f"Atom index {atom} outside valid range 1..{meta.natoms}.")
    return selected


def make_z_groups(meta: DOSMetadata, tol: float = 0.15) -> List[Dict[str, object]]:
    if not meta.z_cart:
        raise ValueError("CONTCAR not available, cannot build z groups.")
    species_map = atom_species_map(meta)
    atoms = list(range(1, meta.natoms + 1))
    records = sorted([(i, species_map.get(i, "X"), meta.z_cart[i - 1]) for i in atoms], key=lambda x: x[2])
    groups: List[Dict[str, object]] = []
    current: List[Tuple[int, str, float]] = []
    for rec in records:
        if not current:
            current = [rec]
            continue
        z_ref = sum(x[2] for x in current) / len(current)
        if abs(rec[2] - z_ref) <= tol:
            current.append(rec)
        else:
            groups.append(_pack_group(current))
            current = [rec]
    if current:
        groups.append(_pack_group(current))
    return groups


def _pack_group(group: Sequence[Tuple[int, str, float]]) -> Dict[str, object]:
    atoms = [x[0] for x in group]
    species = sorted(set(x[1] for x in group))
    z_avg = sum(x[2] for x in group) / len(group)
    return {"atoms": atoms, "species": species, "z_avg": z_avg}


def sum_selected_columns(
    labels: Sequence[str],
    atom_data: Dict[int, List[List[float]]],
    orbitals: Optional[Sequence[str]] = None,
) -> Dict[str, List[float]]:
    if not atom_data:
        raise ValueError("No atom data supplied.")
    npts = len(next(iter(atom_data.values()))[0])

    groups: Dict[str, List[str]]
    if orbitals:
        groups = {orb: expand_orbital_request(orb, labels) for orb in orbitals}
    else:
        groups = default_grouping(labels)

    index_map = {label: i for i, label in enumerate(labels)}
    result: Dict[str, List[float]] = {}
    for out_label, expanded in groups.items():
        vec = [0.0] * npts
        for label in expanded:
            if label not in index_map:
                continue
            j = index_map[label]
            for atom_cols in atom_data.values():
                col = atom_cols[j]
                for i, v in enumerate(col):
                    vec[i] += v
        result[out_label] = vec
    return result


def expand_orbital_request(request: str, labels: Sequence[str]) -> List[str]:
    req = request.strip().lower()
    if req == "all":
        return list(labels)
    if req in {"s", "p", "d", "f"}:
        return [lab for lab in labels if lab.lower().startswith(req)]
    if req in {"s_up", "s_down", "p_up", "p_down", "d_up", "d_down", "f_up", "f_down"}:
        root, spin = req.split("_")
        return [lab for lab in labels if lab.lower().startswith(root) and lab.lower().endswith(spin)]
    if req in {"p_total", "d_total", "f_total"}:
        root = req[0]
        return [lab for lab in labels if lab.lower().startswith(root)]
    exact = [lab for lab in labels if lab.lower() == req]
    if exact:
        return exact
    # allow comma-separated requests passed as a single token
    if "+" in req:
        out: List[str] = []
        for part in req.split("+"):
            out.extend(expand_orbital_request(part, labels))
        return list(dict.fromkeys(out))
    raise ValueError(f"Unknown orbital request '{request}'. Available labels: {', '.join(labels)}")


def default_grouping(labels: Sequence[str]) -> Dict[str, List[str]]:
    lower = [lab.lower() for lab in labels]
    grouped: Dict[str, List[str]] = {}
    if any(lab.startswith("s") for lab in lower):
        grouped["s"] = [lab for lab in labels if lab.lower().startswith("s")]
    if any(lab.startswith("p") for lab in lower):
        grouped["p"] = [lab for lab in labels if lab.lower().startswith("p")]
    if any(lab.startswith("d") for lab in lower):
        grouped["d"] = [lab for lab in labels if lab.lower().startswith("d")]
    if any(lab.startswith("f") for lab in lower):
        grouped["f"] = [lab for lab in labels if lab.lower().startswith("f")]
    if not grouped:
        for lab in labels:
            grouped[lab] = [lab]
    return grouped


def integrate_window(energies: Sequence[float], values: Sequence[float], emin: float, emax: float) -> float:
    points = [(e, v) for e, v in zip(energies, values) if emin <= e <= emax]
    if len(points) < 2:
        return 0.0
    total = 0.0
    for (e1, v1), (e2, v2) in zip(points[:-1], points[1:]):
        total += 0.5 * (v1 + v2) * (e2 - e1)
    return total


def band_center(energies: Sequence[float], values: Sequence[float], emin: float, emax: float) -> float:
    num = integrate_window(energies, [e * v for e, v in zip(energies, values)], emin, emax)
    den = integrate_window(energies, values, emin, emax)
    if abs(den) < 1e-14:
        return float("nan")
    return num / den


def estimate_gap(energies: Sequence[float], dos: Sequence[float], threshold: float = 1e-3) -> Dict[str, float]:
    occ = [(e, d) for e, d in zip(energies, dos) if e <= 0.0]
    unocc = [(e, d) for e, d in zip(energies, dos) if e >= 0.0]
    vbm = max((e for e, d in occ if d > threshold), default=float("nan"))
    cbm = min((e for e, d in unocc if d > threshold), default=float("nan"))
    gap = cbm - vbm if (not math.isnan(vbm) and not math.isnan(cbm) and cbm >= vbm) else float("nan")
    return {"VBM": vbm, "CBM": cbm, "gap": gap}
