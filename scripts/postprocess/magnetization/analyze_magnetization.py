#!/usr/bin/env python3
import argparse
import re
import statistics as stats
from pathlib import Path

COMPONENTS = ["s", "p", "d", "f", "tot"]


def parse_species_info(text: str):
    species = []
    counts = None
    seen_ions_line = False
    for line in text.splitlines():
        if "ions per type" in line:
            counts = [int(x) for x in re.findall(r"\d+", line.split("=")[-1])]
            seen_ions_line = True
            break
        m = re.search(r"VRHFIN\s*=\s*([A-Za-z]{1,3})\s*:", line)
        if m:
            el = m.group(1)
            if not species or species[-1] != el:
                species.append(el)
    if not seen_ions_line or counts is None:
        raise ValueError("No se pudo leer 'ions per type' desde OUTCAR")
    if len(species) != len(counts):
        # fallback conservador: truncar al mínimo común
        n = min(len(species), len(counts))
        species = species[:n]
        counts = counts[:n]
    ranges = []
    start = 1
    for el, n in zip(species, counts):
        end = start + n - 1
        ranges.append({"element": el, "count": n, "start": start, "end": end})
        start = end + 1
    return ranges


def parse_nions(text: str):
    m = re.search(r"NIONS\s*=\s*(\d+)", text)
    if not m:
        raise ValueError("No se pudo leer NIONS desde OUTCAR")
    return int(m.group(1))


def parse_mag_blocks(text: str, nions: int):
    lines = text.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        if "magnetization (x)" in lines[i]:
            block = []
            j = i + 1
            while j < len(lines):
                line = lines[j].strip()
                if re.match(r"^\d+\s+[-+0-9.eE]+", line):
                    parts = line.split()
                    if len(parts) >= 6:
                        ion = int(parts[0])
                        vals = list(map(float, parts[1:6]))
                        block.append({
                            "ion": ion,
                            "s": vals[0],
                            "p": vals[1],
                            "d": vals[2],
                            "f": vals[3],
                            "tot": vals[4],
                        })
                elif line.startswith("tot") and block:
                    break
                j += 1
            if len(block) == nions:
                blocks.append(block)
            i = j
        i += 1
    if not blocks:
        raise ValueError("No se encontraron bloques de magnetización")
    return blocks


def element_ranges(species_ranges, element):
    matches = [r for r in species_ranges if r["element"] == element]
    if not matches:
        raise ValueError(f"El elemento {element} no aparece en OUTCAR")
    return matches


def collect_ions_for_element(species_ranges, element):
    ions = []
    for r in species_ranges:
        if r["element"] == element:
            ions.extend(range(r["start"], r["end"] + 1))
    return ions


def block_to_dict(block):
    return {row["ion"]: row for row in block}


def pick_component(row, component):
    return row[component]


def fmt(x):
    return f"{x: .4f}"


def summary_by_species(final_block, species_ranges):
    data = block_to_dict(final_block)
    out = []
    for r in species_ranges:
        vals = [data[i]["tot"] for i in range(r["start"], r["end"] + 1)]
        absvals = [abs(v) for v in vals]
        out.append((r["element"], r["start"], r["end"], r["count"], sum(vals), max(absvals), stats.mean(absvals)))
    return out


def classify(values, target, tol):
    close = []
    diff = []
    for ion, val in values:
        if abs(abs(val) - target) <= tol:
            close.append((ion, val))
        else:
            diff.append((ion, val))
    return close, diff


def detect_outliers(values, tol):
    nums = [v for _, v in values]
    if not nums:
        return [], None
    med = stats.median(nums)
    out = [(ion, val) for ion, val in values if abs(val - med) > tol]
    return out, med


def main():
    ap = argparse.ArgumentParser(description="Analiza magnetización local desde OUTCAR de VASP")
    ap.add_argument("-o", "--outcar", default="OUTCAR", help="Ruta a OUTCAR")
    ap.add_argument("-e", "--element", help="Elemento a analizar, por ejemplo Ce, Ni, Fe")
    ap.add_argument("--orbital", choices=COMPONENTS, default="tot", help="Componente a analizar")
    ap.add_argument("--target", type=float, help="Magnetización esperada en valor absoluto")
    ap.add_argument("--tol", type=float, default=0.2, help="Tolerancia para target/outliers")
    ap.add_argument("--track", action="store_true", help="Seguir la evolución por paso iónico")
    ap.add_argument("--atoms", help="Lista de átomos separada por comas; si no se da y hay elemento, usa todos los de esa especie")
    ap.add_argument("--top", type=int, default=10, help="Número de átomos a mostrar en listados")
    args = ap.parse_args()

    text = Path(args.outcar).read_text(errors="ignore")
    species_ranges = parse_species_info(text)
    nions = parse_nions(text)
    blocks = parse_mag_blocks(text, nions)
    final_block = blocks[-1]
    final = block_to_dict(final_block)

    print("=== Especies detectadas ===")
    for r in species_ranges:
        print(f"{r['element']:>2}: átomos {r['start']}-{r['end']} (n={r['count']})")

    print("\n=== Resumen final por especie (usando tot) ===")
    for el, start, end, count, tsum, maxabs, meanabs in summary_by_species(final_block, species_ranges):
        print(f"{el:>2} [{start:>3}-{end:<3}]  n={count:<3}  suma(tot)={tsum: .4f}  max|tot|={maxabs: .4f}  media|tot|={meanabs: .4f}")

    if args.element:
        ions = collect_ions_for_element(species_ranges, args.element)
        vals = [(i, pick_component(final[i], args.orbital)) for i in ions]
        vals_sorted = sorted(vals, key=lambda x: abs(x[1]), reverse=True)

        print(f"\n=== {args.element}: componente {args.orbital} en el último paso ===")
        for ion, val in vals_sorted[:args.top]:
            print(f"átomo {ion:>4}: {val: .4f}")
        if len(vals_sorted) > args.top:
            print(f"... ({len(vals_sorted) - args.top} átomos más)")

        outliers, med = detect_outliers(vals, args.tol)
        if med is not None:
            print(f"\nMediana({args.element}, {args.orbital}) = {med: .4f}")
        if outliers:
            print(f"Átomos de {args.element} que difieren más de {args.tol:.3f} respecto a la mediana:")
            for ion, val in sorted(outliers, key=lambda x: abs(x[1] - med), reverse=True):
                print(f"  átomo {ion:>4}: {val: .4f}")
        else:
            print(f"No hay outliers claros dentro de {args.element} con tol = {args.tol:.3f}")

        if args.target is not None:
            close, diff = classify(vals, args.target, args.tol)
            print(f"\nComparación contra target = {args.target:.3f} ± {args.tol:.3f} (en valor absoluto)")
            print("Cercanos al target:", " ".join(str(i) for i, _ in close) if close else "ninguno")
            print("Lejanos al target:", " ".join(str(i) for i, _ in diff) if diff else "ninguno")

    if args.track:
        if args.atoms:
            tracked = [int(x.strip()) for x in args.atoms.split(",") if x.strip()]
        elif args.element:
            tracked = collect_ions_for_element(species_ranges, args.element)
        else:
            raise SystemExit("Para --track debes usar --atoms o --element")

        print(f"\n=== Evolución por paso iónico ({args.orbital}) ===")
        header = "step " + " ".join(f"atom{a}" for a in tracked)
        print(header)
        for istep, block in enumerate(blocks, start=1):
            bdict = block_to_dict(block)
            vals = " ".join(f"{bdict[a][args.orbital]: .4f}" for a in tracked)
            print(f"{istep:>4} {vals}")

        print("\n=== Resumen de evolución ===")
        for a in tracked:
            series = [block_to_dict(b)[a][args.orbital] for b in blocks]
            print(
                f"átomo {a:>4}: inicial={series[0]: .4f}  final={series[-1]: .4f}  min={min(series): .4f}  max={max(series): .4f}"
            )


if __name__ == "__main__":
    main()
