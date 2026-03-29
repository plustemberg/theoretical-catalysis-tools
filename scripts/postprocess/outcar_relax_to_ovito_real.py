#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import re
import tempfile
from pathlib import Path
from typing import Optional, Sequence

# Needed before importing OVITO's OpenGL renderer in standalone scripts.
os.environ.setdefault('OVITO_GUI_MODE', '1')

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    from ovito.io import import_file
    from ovito.vis import Viewport, OpenGLRenderer, TachyonRenderer
    OVITO_AVAILABLE = True
    OVITO_IMPORT_ERROR = None
except Exception as exc:
    OVITO_AVAILABLE = False
    OVITO_IMPORT_ERROR = str(exc)

FLOAT_RE = r"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?"

# Optional custom colors. Leave empty to use OVITO defaults derived from element names.
CUSTOM_ELEMENT_COLORS = {
    # 'Ce': (0.94, 0.91, 0.69),
    # 'O':  (1.00, 0.00, 0.00),
    # 'Ni': (0.00, 0.28, 1.00),
    # 'C':  (0.75, 0.75, 0.75),
    # 'H':  (1.00, 1.00, 1.00),
}


def parse_symbol_from_vrhfin(line: str) -> Optional[str]:
    m = re.search(r"VRHFIN\s*=\s*([A-Za-z]{1,3})\s*:", line)
    return m.group(1) if m else None


def line_is_separator(line: str) -> bool:
    s = line.strip()
    return bool(s) and set(s) == {'-'}


def looks_like_position_line(line: str) -> bool:
    vals = line.split()
    if len(vals) < 6:
        return False
    try:
        [float(x) for x in vals[:6]]
        return True
    except Exception:
        return False


def build_symbols(ions_per_type, vrhfin_symbols, natoms):
    if ions_per_type and vrhfin_symbols and len(vrhfin_symbols) >= len(ions_per_type):
        symbols = []
        for s, n in zip(vrhfin_symbols[:len(ions_per_type)], ions_per_type):
            symbols.extend([s] * n)
        if len(symbols) == natoms:
            return symbols, False
    return ['X'] * natoms, True


def parse_outcar(path: Path):
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    ions_per_type = None
    vrhfin_symbols = []
    current_cell = None
    last_mag = None
    frames = []

    i = 0
    nlines = len(lines)
    while i < nlines:
        line = lines[i]

        if 'ions per type =' in line:
            try:
                ions_per_type = [int(x) for x in line.split('=', 1)[1].split()]
            except Exception:
                pass

        if 'VRHFIN' in line:
            sym = parse_symbol_from_vrhfin(line)
            if sym:
                vrhfin_symbols.append(sym)

        if 'direct lattice vectors' in line.lower() and i + 3 < nlines:
            try:
                cell = []
                for j in range(1, 4):
                    vals = lines[i + j].split()
                    cell.append([float(vals[0]), float(vals[1]), float(vals[2])])
                current_cell = np.array(cell, dtype=float)
                i += 4
                continue
            except Exception:
                pass

        if 'number of electron' in line and 'magnetization' in line:
            m = re.search(r'magnetization\s+(' + FLOAT_RE + r')\s*$', line.strip())
            if m:
                try:
                    last_mag = float(m.group(1))
                except Exception:
                    pass

        if 'POSITION' in line and 'TOTAL-FORCE' in line:
            i += 1
            while i < nlines and (not lines[i].strip() or line_is_separator(lines[i])):
                i += 1

            positions, forces = [], []
            while i < nlines and looks_like_position_line(lines[i]):
                vals = lines[i].split()
                x, y, z, fx, fy, fz = map(float, vals[:6])
                positions.append([x, y, z])
                forces.append([fx, fy, fz])
                i += 1

            if not positions:
                raise RuntimeError('Se encontró POSITION/TOTAL-FORCE pero no se pudieron leer átomos.')

            while i < nlines and (not lines[i].strip() or line_is_separator(lines[i])):
                i += 1

            energy = None
            j = i
            search_limit = min(i + 500, nlines)
            while j < search_limit:
                m = re.search(r'free\s+energy\s+TOTEN\s*=\s*(' + FLOAT_RE + r')\s*eV', lines[j])
                if m:
                    energy = float(m.group(1))
                    break
                if 'POSITION' in lines[j] and 'TOTAL-FORCE' in lines[j]:
                    break
                j += 1
            if energy is None:
                raise RuntimeError('No se encontró TOTEN después de un bloque POSITION/TOTAL-FORCE.')

            pos = np.array(positions, dtype=float)
            frc = np.array(forces, dtype=float)
            if current_cell is None:
                mins = pos.min(axis=0)
                maxs = pos.max(axis=0)
                span = np.maximum(maxs - mins, 10.0)
                current_cell = np.diag(span + 5.0)

            norms = np.linalg.norm(frc, axis=1)
            frames.append({
                'positions': pos,
                'forces': frc,
                'cell': np.array(current_cell, dtype=float),
                'energy': float(energy),
                'magnetization': None if last_mag is None else float(last_mag),
                'max_force': float(np.max(norms)),
                'rms_force': float(np.sqrt(np.mean(norms**2))),
            })
            i = j + 1
            continue

        i += 1

    if not frames:
        raise RuntimeError('No se encontraron bloques iónicos POSITION/TOTAL-FORCE en el OUTCAR.')

    natoms = len(frames[0]['positions'])
    for k, fr in enumerate(frames, start=1):
        if len(fr['positions']) != natoms:
            raise RuntimeError(f'El frame {k} tiene {len(fr["positions"])} átomos; el primero tiene {natoms}.')

    symbols, used_generic = build_symbols(ions_per_type, vrhfin_symbols, natoms)
    return frames, symbols, used_generic


def _is_integer_line(tokens: Sequence[str]) -> bool:
    try:
        [int(x) for x in tokens]
        return True
    except Exception:
        return False


def parse_poscar_like(path: Path, fallback_symbols=None):
    raw = [ln.rstrip() for ln in path.read_text(encoding='utf-8', errors='replace').splitlines() if ln.strip()]
    if len(raw) < 8:
        raise RuntimeError(f'{path} es demasiado corto para ser POSCAR/CONTCAR.')
    scale = float(raw[1].split()[0])
    lattice = np.array([[float(x) for x in raw[i].split()[:3]] for i in range(2, 5)], dtype=float)
    lattice *= abs(scale)

    line5 = raw[5].split()
    if _is_integer_line(line5):
        counts = [int(x) for x in line5]
        if fallback_symbols:
            uniq = []
            for s in fallback_symbols:
                if s not in uniq:
                    uniq.append(s)
            symbols_unique = uniq[:len(counts)]
        else:
            symbols_unique = [f'X{i+1}' for i in range(len(counts))]
        idx = 6
    else:
        symbols_unique = line5
        counts = [int(x) for x in raw[6].split()]
        idx = 7

    if raw[idx].lower().startswith('selective'):
        idx += 1
    mode = raw[idx].lower()
    idx += 1
    natoms = sum(counts)
    coords = np.array([[float(x) for x in raw[idx+j].split()[:3]] for j in range(natoms)], dtype=float)
    positions = coords @ lattice if mode.startswith('d') else coords * abs(scale)

    symbols = []
    for s, n in zip(symbols_unique, counts):
        symbols.extend([s] * n)
    return {'cell': lattice, 'positions': positions, 'symbols': symbols}


def get_final_structure(calc_dir: Path, frames, symbols):
    for fname in ('CONTCAR', 'POSCAR'):
        p = calc_dir / fname
        if p.is_file():
            try:
                return parse_poscar_like(p, fallback_symbols=symbols), fname, p
            except Exception:
                pass
    return {'cell': np.array(frames[-1]['cell']), 'positions': np.array(frames[-1]['positions']), 'symbols': list(symbols)}, 'last OUTCAR frame', None


def write_extxyz(path: Path, frames, symbols):
    energies = np.array([fr['energy'] for fr in frames], dtype=float)
    de = energies - energies[0]
    with path.open('w', encoding='utf-8') as fh:
        for step, (fr, dE) in enumerate(zip(frames, de), start=1):
            nat = len(symbols)
            fh.write(f'{nat}\n')
            cell_flat = ' '.join(f'{x:.10f}' for x in fr['cell'].reshape(-1))
            parts = [
                f'Lattice="{cell_flat}"',
                'Properties=species:S:1:pos:R:3:forces:R:3',
                'pbc="T T T"',
                f'step={step}',
                f'energy={fr["energy"]:.10f}',
                f'delta_e={dE:.10f}',
                f'max_force={fr["max_force"]:.10f}',
            ]
            if fr['magnetization'] is not None:
                parts.append(f'magnetization={fr["magnetization"]:.10f}')
            fh.write(' '.join(parts) + '\n')
            for s, p, f in zip(symbols, fr['positions'], fr['forces']):
                fh.write(f'{s:2s} {p[0]: .10f} {p[1]: .10f} {p[2]: .10f} {f[0]: .10f} {f[1]: .10f} {f[2]: .10f}\n')


def write_single_structure_extxyz(path: Path, structure):
    cell = np.array(structure['cell'], dtype=float)
    positions = np.array(structure['positions'], dtype=float)
    symbols = list(structure['symbols'])
    with path.open('w', encoding='utf-8') as fh:
        fh.write(f'{len(symbols)}\n')
        cell_flat = ' '.join(f'{x:.10f}' for x in cell.reshape(-1))
        fh.write(f'Lattice="{cell_flat}" Properties=species:S:1:pos:R:3 pbc="T T T"\n')
        for s, p in zip(symbols, positions):
            fh.write(f'{s:2s} {p[0]: .10f} {p[1]: .10f} {p[2]: .10f}\n')


def write_summary_csv(path: Path, frames):
    energies = np.array([fr['energy'] for fr in frames], dtype=float)
    de = energies - energies[0]
    with path.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['step','energy_eV','deltaE_vs_first_eV','max_force_eVA','rms_force_eVA','total_magnetization'])
        for step, (fr, dE) in enumerate(zip(frames, de), start=1):
            w.writerow([step, f'{fr["energy"]:.10f}', f'{dE:.10f}', f'{fr["max_force"]:.10f}', f'{fr["rms_force"]:.10f}', '' if fr['magnetization'] is None else f'{fr["magnetization"]:.10f}'])


def simple_plot(path: Path, x, y, xlabel, ylabel, title):
    plt.figure(figsize=(7.0, 4.5))
    plt.plot(x, y, marker='o', markersize=3)
    if ylabel.startswith('ΔE'):
        plt.axhline(0.0, linewidth=1.0)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=200, facecolor='white')
    plt.close()


def _install_color_modifier(pipeline, custom_colors: dict[str, tuple[float, float, float]]):
    def color_particles(frame, data):
        pt = data.particles.particle_types
        tids = np.asarray(pt[...], dtype=int)
        colors = np.empty((len(tids), 3), dtype=float)
        for i, tid in enumerate(tids):
            ptype = pt.type_by_id(int(tid))
            base_color = tuple(getattr(ptype, 'color', (0.7, 0.7, 0.7)))
            colors[i] = custom_colors.get(ptype.name, base_color)
        data.particles_.create_property('Color', data=colors)
    pipeline.modifiers.append(color_particles)


def render_views_with_ovito(
    source_path: Path,
    out_prefix: Path,
    atom_scale: float = 1.20,
    use_custom_colors: bool = False,
    renderer_name: str = 'opengl',
    image_size: tuple[int, int] = (1600, 1200),
):
    if not OVITO_AVAILABLE:
        raise RuntimeError(f'OVITO no está disponible: {OVITO_IMPORT_ERROR}')

    pipeline = import_file(str(source_path))
    if use_custom_colors and CUSTOM_ELEMENT_COLORS:
        _install_color_modifier(pipeline, CUSTOM_ELEMENT_COLORS)

    pipeline.add_to_scene()
    data = pipeline.compute()

    data.particles.vis.scaling = atom_scale
    if getattr(data, 'cell', None) is not None:
        data.cell.vis.enabled = True
        if hasattr(data.cell.vis, 'render_cell'):
            data.cell.vis.render_cell = True
        data.cell.vis.rendering_color = (0.70, 0.70, 0.70)

    if renderer_name.lower() == 'opengl':
        renderer = OpenGLRenderer()
    elif renderer_name.lower() == 'tachyon':
        renderer = TachyonRenderer()
    else:
        raise ValueError(f'Renderer no soportado: {renderer_name}')

    views = {
        'xy': Viewport(type=Viewport.Type.Top),
        'xz': Viewport(type=Viewport.Type.Front),
        'yz': Viewport(type=Viewport.Type.Right),
        'iso': Viewport(type=Viewport.Type.Ortho, camera_dir=(2, 1, -1)),
    }

    written = []
    for key, vp in views.items():
        vp.zoom_all(size=image_size)
        outfile = out_prefix.parent / f'{out_prefix.name}_view_{key}.png'
        vp.render_image(
            filename=str(outfile),
            size=image_size,
            renderer=renderer,
            background=(1.0, 1.0, 1.0),
        )
        written.append(str(outfile))

    pipeline.remove_from_scene()
    return written


def process_one(outcar: Path, output_prefix=None, atom_scale=1.20, renderer_name='opengl', use_custom_colors=False):
    calc_dir = outcar.parent
    frames, symbols, used_generic = parse_outcar(outcar)
    structure, view_source, structure_path = get_final_structure(calc_dir, frames, symbols)
    if any(s == 'X' for s in symbols) and not any(s == 'X' for s in structure['symbols']) and len(structure['symbols']) == len(symbols):
        symbols = structure['symbols']
    if len(structure['symbols']) == len(symbols):
        structure['symbols'] = list(symbols)

    prefix_name = output_prefix if output_prefix else 'relax'
    prefix = calc_dir / prefix_name
    extxyz = Path(str(prefix) + '.extxyz')
    summary = Path(str(prefix) + '_summary.csv')
    energy_png = Path(str(prefix) + '_energy.png')
    force_png = Path(str(prefix) + '_forces.png')
    mag_png = Path(str(prefix) + '_magnetization.png')

    write_extxyz(extxyz, frames, symbols)
    write_summary_csv(summary, frames)

    steps = np.arange(1, len(frames)+1)
    energies = np.array([fr['energy'] for fr in frames], float)
    de = energies - energies[0]
    fmax = np.array([fr['max_force'] for fr in frames], float)
    simple_plot(energy_png, steps, de, 'Ionic step', 'ΔE relative to first step (eV)', 'Relaxation energy profile')
    simple_plot(force_png, steps, fmax, 'Ionic step', 'Max atomic |F| (eV/Å)', 'Force convergence along relaxation')

    mags = [fr['magnetization'] for fr in frames]
    has_mag = any(m is not None for m in mags)
    if has_mag:
        msteps = [i+1 for i, m in enumerate(mags) if m is not None]
        mvals = [m for m in mags if m is not None]
        simple_plot(mag_png, msteps, mvals, 'Ionic step', 'Total magnetization', 'Total magnetization vs ionic step')

    temp_render_file = None
    if structure_path is None:
        temp_render_file = calc_dir / '_ovito_last_frame.extxyz'
        write_single_structure_extxyz(temp_render_file, structure)
        render_source = temp_render_file
    else:
        render_source = structure_path

    view_files = render_views_with_ovito(
        render_source,
        prefix,
        atom_scale=atom_scale,
        use_custom_colors=use_custom_colors,
        renderer_name=renderer_name,
    )

    if temp_render_file is not None and temp_render_file.exists():
        try:
            temp_render_file.unlink()
        except Exception:
            pass

    return {
        'dir': str(calc_dir), 'outcar': str(outcar), 'frames': len(frames), 'natoms': len(symbols), 'prefix': str(prefix),
        'view_source': view_source, 'used_generic_species': used_generic, 'has_mag': has_mag,
        'files': [str(extxyz), str(summary), str(energy_png), str(force_png)] + ([str(mag_png)] if has_mag else []) + view_files
    }


def find_outcars(root: Path):
    found = []
    for dirpath, _, filenames in os.walk(root):
        if 'OUTCAR' in filenames:
            found.append(Path(dirpath) / 'OUTCAR')
    return sorted(found)


def main():
    parser = argparse.ArgumentParser(description='Extrae trayectoria de relajación desde OUTCAR, genera extxyz, CSV, gráficos y vistas PNG renderizadas con OVITO.')
    parser.add_argument('path', help='OUTCAR, carpeta de cálculo, o carpeta raíz si usas --recursive')
    parser.add_argument('-o', '--output-prefix', default=None, help='Prefijo de salida en modo no recursivo. Por defecto: relax')
    parser.add_argument('--recursive', action='store_true', help='Procesa todos los subdirectorios con OUTCAR')
    parser.add_argument('--atom-scale', type=float, default=1.20, help='Escala global del tamaño de las esferas en los PNG de OVITO')
    parser.add_argument('--renderer', choices=['opengl', 'tachyon'], default='opengl', help='Motor de render para OVITO')
    parser.add_argument('--use-custom-colors', action='store_true', help='Usa el diccionario CUSTOM_ELEMENT_COLORS en lugar de los colores por defecto de OVITO')
    args = parser.parse_args()

    target = Path(args.path).resolve()
    if not target.exists():
        raise FileNotFoundError(f'No existe la ruta: {target}')

    if args.recursive:
        if not target.is_dir():
            raise RuntimeError('--recursive requiere una carpeta.')
        outcars = find_outcars(target)
        if not outcars:
            raise RuntimeError(f'No se encontraron OUTCAR bajo: {target}')
        print(f'Se encontraron {len(outcars)} OUTCAR.')
        for outcar in outcars:
            try:
                r = process_one(
                    outcar,
                    atom_scale=args.atom_scale,
                    renderer_name=args.renderer,
                    use_custom_colors=args.use_custom_colors,
                )
                print(f'[OK] {r["outcar"]} -> {r["prefix"]}')
            except Exception as exc:
                print(f'[FAILED] {outcar}: {exc}')
        return

    if target.is_file():
        if target.name != 'OUTCAR':
            raise RuntimeError('En modo archivo debes pasar un fichero llamado OUTCAR.')
        outcar = target
    elif target.is_dir():
        outcar = target / 'OUTCAR'
        if not outcar.is_file():
            raise RuntimeError(f'La carpeta no contiene OUTCAR: {target}')
    else:
        raise RuntimeError(f'Ruta no soportada: {target}')

    r = process_one(
        outcar,
        output_prefix=args.output_prefix,
        atom_scale=args.atom_scale,
        renderer_name=args.renderer,
        use_custom_colors=args.use_custom_colors,
    )
    print(f'Directory               : {r["dir"]}')
    print(f'OUTCAR                  : {r["outcar"]}')
    print(f'Frames extracted        : {r["frames"]}')
    print(f'Atoms per frame         : {r["natoms"]}')
    print(f'Output prefix           : {r["prefix"]}')
    print(f'Views generated from    : {r["view_source"]}')
    if r['used_generic_species']:
        print('Species labels          : generic X (metadatos del OUTCAR insuficientes)')
    for f in r['files']:
        print(f'Wrote                   : {f}')


if __name__ == '__main__':
    main()
