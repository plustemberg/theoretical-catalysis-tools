#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple


MAG_SECTION_RE = re.compile(r"^\s*magnetization \(x\)\s*$", re.MULTILINE)
HEADER_RE = re.compile(r"^\s*#\s+of\s+ion", re.IGNORECASE)
DASH_RE = re.compile(r"^\s*-+\s*$")


def normalize_newline(s: str) -> str:
    if s.endswith("\r\n"):
        return "\r\n"
    if s.endswith("\n"):
        return "\n"
    return "\n"


def rebuild_line(tokens: List[str], original_line: str) -> str:
    return "  ".join(str(t) for t in tokens) + normalize_newline(original_line)


def parse_last_magnetization_f(outcar_path: Path) -> List[Tuple[int, float]]:
    try:
        text = outcar_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError(f"No se pudo leer {outcar_path}: {e}")

    matches = list(MAG_SECTION_RE.finditer(text))
    if not matches:
        raise RuntimeError("No se encontró ninguna sección 'magnetization (x)' en el OUTCAR")

    last_start = matches[-1].start()
    block = text[last_start:].splitlines()

    # Buscar cabecera y comienzo de datos
    data_started = False
    found_header = False
    values: List[Tuple[int, float]] = []

    for line in block[1:]:
        if not found_header:
            if HEADER_RE.search(line):
                found_header = True
            continue

        if found_header and not data_started:
            if DASH_RE.match(line):
                data_started = True
            continue

        stripped = line.strip()
        if not stripped:
            break
        if DASH_RE.match(line):
            continue
        if stripped.lower().startswith("tot"):
            break

        parts = line.split()
        if len(parts) < 5:
            continue

        try:
            ion_index = int(parts[0])
            f_value = float(parts[-1])
        except ValueError:
            continue

        values.append((ion_index, f_value))

    if not values:
        raise RuntimeError("No se pudieron extraer valores de la última tabla 'magnetization (x)'")

    return values


def ce3_indices_from_outcar(outcar_path: Path, threshold: float) -> List[int]:
    values = parse_last_magnetization_f(outcar_path)
    return [idx for idx, fval in values if abs(fval) > threshold]


def read_contcar_header(contcar_path: Path) -> Tuple[List[str], List[str], List[str]]:
    try:
        with contcar_path.open("r", encoding="utf-8", errors="surrogateescape", newline="") as f:
            lines = f.readlines()
    except Exception as e:
        raise RuntimeError(f"No se pudo leer {contcar_path}: {e}")

    if len(lines) < 7:
        raise RuntimeError("El CONTCAR tiene menos de 7 líneas")

    species = lines[5].split()
    counts = lines[6].split()

    if len(species) != len(counts):
        raise RuntimeError(
            f"Número de especies ({len(species)}) distinto del número de conteos ({len(counts)})"
        )

    return lines, species, counts


def build_ce_la_segments(n_ce: int, la_indices: List[int]) -> Tuple[List[str], List[int]]:
    la_sorted = sorted(i for i in la_indices if 1 <= i <= n_ce)
    if len(set(la_sorted)) != len(la_sorted):
        raise RuntimeError("Hay índices Ce3+ duplicados dentro del bloque de Ce")

    new_species: List[str] = []
    new_counts: List[int] = []

    current = 1
    for la_idx in la_sorted:
        ce_count = la_idx - current
        if ce_count > 0:
            new_species.append("Ce")
            new_counts.append(ce_count)
        new_species.append("La")
        new_counts.append(1)
        current = la_idx + 1

    tail = n_ce - current + 1
    if tail > 0:
        new_species.append("Ce")
        new_counts.append(tail)

    if not new_species:
        new_species = ["Ce"]
        new_counts = [n_ce]

    return new_species, new_counts


def process_pair(
    contcar_path: Path,
    outcar_path: Path,
    threshold: float,
    output_name: Optional[str],
    dry_run: bool,
    verbose: bool,
) -> bool:
    lines, species, counts = read_contcar_header(contcar_path)

    if not species:
        raise RuntimeError("La línea de especies del CONTCAR está vacía")
    if species[0] != "Ce":
        raise RuntimeError(
            f"Se esperaba que la primera especie fuera 'Ce', pero se encontró '{species[0]}'"
        )

    try:
        int_counts = [int(x) for x in counts]
    except ValueError:
        raise RuntimeError("La línea de cantidades del CONTCAR no contiene solo enteros")

    n_ce = int_counts[0]
    ce3_all = ce3_indices_from_outcar(outcar_path, threshold)
    ce3_in_ce_block = [idx for idx in ce3_all if 1 <= idx <= n_ce]
    ce3_outside_ce_block = [idx for idx in ce3_all if idx > n_ce]

    new_ce_species, new_ce_counts = build_ce_la_segments(n_ce, ce3_in_ce_block)
    new_species = new_ce_species + species[1:]
    new_counts = new_ce_counts + int_counts[1:]

    new_lines = lines[:]
    new_lines[5] = rebuild_line(new_species, lines[5])
    new_lines[6] = rebuild_line([str(x) for x in new_counts], lines[6])

    out_path = contcar_path if output_name is None else contcar_path.with_name(output_name)

    if verbose or dry_run:
        print(f"[DIR] {contcar_path.parent}")
        print(f"  Ce3+ detectados (|f| > {threshold}): {ce3_all}")
        print(f"  Ce3+ dentro del bloque Ce      : {ce3_in_ce_block}")
        if ce3_outside_ce_block:
            print(f"  Aviso: hay índices > nCe que no se marcan como La: {ce3_outside_ce_block}")
        print(f"  Línea 6 nueva: {'  '.join(new_species)}")
        print(f"  Línea 7 nueva: {'  '.join(str(x) for x in new_counts)}")

    if dry_run:
        print(f"  [DRY-RUN] Escribiría: {out_path}")
        return True

    try:
        with out_path.open("w", encoding="utf-8", errors="surrogateescape", newline="") as f:
            f.writelines(new_lines)
    except Exception as e:
        raise RuntimeError(f"No se pudo escribir {out_path}: {e}")

    print(f"  [OK] {contcar_path} -> {out_path}")
    return True


def find_pairs(root: Path, contcar_name: str, outcar_name: str) -> List[Tuple[Path, Path]]:
    pairs: List[Tuple[Path, Path]] = []
    for contcar_path in sorted(root.rglob(contcar_name)):
        if not contcar_path.is_file():
            continue
        outcar_path = contcar_path.with_name(outcar_name)
        if outcar_path.is_file():
            pairs.append((contcar_path, outcar_path))
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Busca recursivamente carpetas que contengan CONTCAR y OUTCAR, "
            "lee la última 'magnetization (x)' del OUTCAR y marca como 'La' "
            "los Ce con |f| por encima del umbral."
        )
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Directorio raíz donde buscar recursivamente (por defecto: directorio actual)",
    )
    parser.add_argument(
        "--contcar-name",
        default="CONTCAR",
        help="Nombre del archivo CONTCAR a buscar (por defecto: CONTCAR)",
    )
    parser.add_argument(
        "--outcar-name",
        default="OUTCAR",
        help="Nombre del archivo OUTCAR a buscar (por defecto: OUTCAR)",
    )
    parser.add_argument(
        "-o",
        "--output-name",
        default="CONTCAR_Ce3",
        help=(
            "Nombre del archivo de salida dentro de cada carpeta. "
            "Por defecto: CONTCAR_Ce3. Usa --in-place para sobrescribir CONTCAR."
        ),
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Sobrescribe el CONTCAR original en lugar de crear un archivo nuevo",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=0.8,
        help="Umbral para |f| en la última magnetization (x) (por defecto: 0.8)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra qué haría, pero no escribe archivos",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Reduce la salida por pantalla",
    )

    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"Error: {root} no es un directorio válido", file=sys.stderr)
        return 1

    output_name = None if args.in_place else args.output_name

    pairs = find_pairs(root, args.contcar_name, args.outcar_name)
    if not pairs:
        print(
            f"No se encontraron carpetas con ambos archivos '{args.contcar_name}' y '{args.outcar_name}' en {root}"
        )
        return 0

    ok = 0
    fail = 0
    for contcar_path, outcar_path in pairs:
        try:
            process_pair(
                contcar_path=contcar_path,
                outcar_path=outcar_path,
                threshold=args.threshold,
                output_name=output_name,
                dry_run=args.dry_run,
                verbose=not args.quiet,
            )
            ok += 1
        except Exception as e:
            fail += 1
            print(f"[ERROR] {contcar_path.parent}: {e}")

    print(f"\nResumen: {ok} carpeta(s) procesadas correctamente, {fail} con error.")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
