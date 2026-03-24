# `extract_info_jobs.sh`

## Purpose

This script is used to scan multiple calculation subdirectories and extract a compact summary from VASP standard output files named `job*.out`.

It is useful when many jobs have been launched simultaneously in different folders and you want a quick overview of the latest reported values in each output file without opening them one by one.

For every `job*.out` file found recursively from the current directory, the script:

- searches for the last line containing `E0=`;
- extracts the ionic iteration index;
- extracts the final reported `E0` value;
- extracts the final reported `mag` value;
- prints everything in a single line together with the file path.

## Typical use case

Run this script from the parent directory that contains many calculation folders. The script will descend into all subdirectories automatically and inspect every file matching:

```bash
job*.out
```

This is practical for checking the current status of many VASP jobs after batch submission on MN5.

## How to use it

Give execution permission:

```bash
chmod +x extraer_info_jobs1.sh
```

Run it from the directory where you want the recursive search to start:

```bash
./extraer_info_jobs1.sh
```

You can also run it explicitly with `bash`:

```bash
bash extraer_info_jobs1.sh
```

## Expected output

For each matching file, the script prints one line like:

```bash
./calc_01/job.out  Iter: 42  E0= -1234.56789  mag= 2.000
```

If no valid `E0=` line is found in a file, it prints:

```bash
./calc_02/job.out  No se encontró línea con E0=
```

## Variables used inside the script

This script does not require command-line arguments or external environment variables.

Internal variables:

- `filepath`: full path of each `job*.out` file found by `find`.
- `last_line`: last line in the file containing `E0=`.
- `iter`: first field of the selected line, interpreted as the iteration number.
- `e0`: value extracted from `E0=` and formatted with 5 decimals.
- `mag`: value extracted from `mag=` and formatted with 3 decimals.

## Notes

- The script assumes that the relevant line contains both `E0=` and `mag=` in a format compatible with the `grep` expressions used.
- It only keeps the **last** occurrence of a line containing `E0=` in each file.
- The search is recursive and starts from the current directory (`.`).
- The script does not modify any files.

## Complete script

```bash
#!/bin/bash

# Buscar todos los archivos job*.out en subdirectorios
find . -type f -name "job*.out" | while read -r filepath; do
  # Buscar la última línea con E0= y mag=
  last_line=$(grep -i "E0=" "$filepath" | tail -n 1)

  if [[ -n "$last_line" ]]; then
    # Extraer número de iteración (usualmente al comienzo de la línea)
    iter=$(echo "$last_line" | awk '{print $1}')

    # Extraer valor de E0
    e0=$(echo "$last_line" | grep -oE "E0= *[-+]?[0-9.]+E?[-+]?[0-9]*" | sed 's/E0= *//' | awk '{printf "%.5f", $1}')

    # Extraer valor de mag
    mag=$(echo "$last_line" | grep -oE "mag= *[-+]?[0-9.]+E?[-+]?[0-9]*" | sed 's/mag= *//' | awk '{printf "%.3f", $1}')

    # Imprimir en una sola línea
    echo "$filepath  Iter: $iter  E0= $e0  mag= $mag"
  else
    echo "$filepath  No se encontró línea con E0="
  fi
done
```
