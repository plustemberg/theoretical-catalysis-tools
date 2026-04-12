# README — `contcar_mark_ce3_recursive.py`

## Qué hace este script

`contcar_mark_ce3_recursive.py` busca **recursivamente** carpetas que contengan al mismo tiempo un `CONTCAR` y un `OUTCAR`. En cada carpeta encontrada:

1. lee la **última** sección `magnetization (x)` del `OUTCAR`,
2. toma la columna **`f`**,
3. identifica los átomos cuyo valor cumple `|f| > umbral`,
4. restringe esa selección al **bloque inicial de Ce** del `CONTCAR`,
5. y reescribe las líneas de **especies** y **número de átomos** para que los `Ce3+` queden etiquetados como `La`.

El objetivo es generar un `CONTCAR` donde los `Ce3+` queden **explícitos visualmente** sin modificar las coordenadas atómicas.

---

## Idea general del procedimiento

El script asume el orden estándar de VASP en el `CONTCAR`:

- la línea 6 contiene las especies,
- la línea 7 contiene el número de átomos de cada especie,
- y las coordenadas están agrupadas por especie en el mismo orden.

Por ejemplo, si el `CONTCAR` tiene:

```text
Ce O Ni
32 64 6
```

y en la última `magnetization (x)` del `OUTCAR` los índices con `|f| > 0.8` son:

```text
3 10 16
```

entonces el script transforma:

```text
Ce O Ni
32 64 6
```

en:

```text
Ce La Ce La Ce La Ce O Ni
2 1 6 1 5 1 16 64 6
```

Es decir, cada `Ce3+` se separa como un bloque individual `La` dentro del bloque original de Ce.

---

## Qué modifica y qué no modifica

### Modifica

Solo las siguientes líneas del `CONTCAR`:

- **línea 6**: especies químicas
- **línea 7**: número de átomos por especie

### No modifica

- coordenadas atómicas
- factor de escala
- vectores de red
- modo `Selective dynamics`
- posiciones atómicas
- el `OUTCAR`

---

## Suposiciones importantes

El script actual funciona correctamente si se cumplen estas condiciones:

1. La **primera especie** del `CONTCAR` es `Ce`.
2. El número de átomos de Ce está en el **primer valor** de la línea de conteos.
3. Los átomos están ordenados por bloques de especie como en un `CONTCAR/POSCAR` estándar de VASP.
4. La sección `magnetization (x)` existe en el `OUTCAR`.
5. La columna final de esa tabla corresponde al valor **`f`**.

### Ejemplos válidos

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

Mientras `Ce` siga siendo la **primera especie**, el script puede actuar sobre ese primer bloque.

### Ejemplo no válido con esta versión

```text
O Ce Ni
64 32 6
```

En ese caso el script fallará, porque espera que el bloque inicial corresponda a `Ce`.

---

## Qué pasa si detecta átomos con `|f| > umbral` fuera del bloque de Ce

El script puede encontrar índices con magnetización alta que estén **fuera** del bloque inicial de Ce. En ese caso:

- los muestra por pantalla como aviso,
- pero **no los marca como `La`**,
- porque solo transforma los índices que pertenecen al bloque de Ce.

Esto evita etiquetar otras especies incorrectamente.

---

## Archivos de entrada esperados

Por defecto, en cada carpeta el script busca:

- `CONTCAR`
- `OUTCAR`

Solo procesa carpetas donde **ambos archivos** existen.

---

## Archivo de salida

Por defecto, el script **no sobrescribe** el `CONTCAR`. En su lugar crea:

```text
CONTCAR_Ce3
```

Si se desea, puede sobrescribir el archivo original usando la opción `--in-place`.

---

## Uso básico

### Buscar desde el directorio actual

```bash
python contcar_mark_ce3_recursive.py .
```

Esto recorre el directorio actual y todos sus subdirectorios, y procesa cada carpeta que contenga `CONTCAR` y `OUTCAR`.

---

## Opciones disponibles

### `root`

Directorio raíz desde donde empezar la búsqueda recursiva.

```bash
python contcar_mark_ce3_recursive.py /ruta/al/proyecto
```

---

### `--contcar-name`

Permite cambiar el nombre del archivo `CONTCAR` buscado.

```bash
python contcar_mark_ce3_recursive.py . --contcar-name CONTCAR.relax
```

---

### `--outcar-name`

Permite cambiar el nombre del archivo `OUTCAR` buscado.

```bash
python contcar_mark_ce3_recursive.py . --outcar-name OUTCAR.relax
```

---

### `-o`, `--output-name`

Permite definir el nombre del archivo de salida en cada carpeta.

```bash
python contcar_mark_ce3_recursive.py . -o CONTCAR_marked
```

Por defecto usa:

```text
CONTCAR_Ce3
```

---

### `--in-place`

Sobrescribe el `CONTCAR` original en lugar de crear un archivo nuevo.

```bash
python contcar_mark_ce3_recursive.py . --in-place
```

Usa esta opción con cuidado.

---

### `-t`, `--threshold`

Define el umbral aplicado sobre `|f|` en la última `magnetization (x)`.

Valor por defecto:

```text
0.8
```

Ejemplo:

```bash
python contcar_mark_ce3_recursive.py . --threshold 0.85
```

El criterio aplicado es:

```text
|f| > threshold
```

---

### `--dry-run`

Muestra qué haría el script, pero **no escribe archivos**.

```bash
python contcar_mark_ce3_recursive.py . --dry-run
```

Es la mejor opción para verificar el resultado antes de modificar nada.

---

### `-q`, `--quiet`

Reduce la información mostrada por pantalla.

```bash
python contcar_mark_ce3_recursive.py . --quiet
```

---

## Ejemplos de uso

### 1. Ver qué carpetas serían procesadas, sin escribir nada

```bash
python contcar_mark_ce3_recursive.py . --dry-run
```

### 2. Procesar todo recursivamente y guardar como `CONTCAR_Ce3`

```bash
python contcar_mark_ce3_recursive.py .
```

### 3. Sobrescribir todos los `CONTCAR`

```bash
python contcar_mark_ce3_recursive.py . --in-place
```

### 4. Usar nombres de archivos diferentes

```bash
python contcar_mark_ce3_recursive.py . --contcar-name POSCAR --outcar-name OUTCAR.relax
```

### 5. Cambiar el umbral de identificación de `Ce3+`

```bash
python contcar_mark_ce3_recursive.py . -t 1.0
```

---

## Salida por pantalla

En modo normal, para cada carpeta el script muestra algo como:

```text
[DIR] /ruta/a/la/carpeta
  Ce3+ detectados (|f| > 0.8): [3, 10, 16]
  Ce3+ dentro del bloque Ce      : [3, 10, 16]
  Línea 6 nueva: Ce  La  Ce  La  Ce  La  Ce  O  Ni
  Línea 7 nueva: 2  1  6  1  5  1  16  64  6
  [OK] /ruta/a/la/carpeta/CONTCAR -> /ruta/a/la/carpeta/CONTCAR_Ce3
```

Si encuentra índices fuera del bloque de Ce, añade un aviso como:

```text
Aviso: hay índices > nCe que no se marcan como La: [...]
```

Al final, imprime un resumen global:

```text
Resumen: X carpeta(s) procesadas correctamente, Y con error.
```

---

## Limitaciones de esta versión

1. **Exige que `Ce` sea la primera especie** del `CONTCAR`.
2. **No verifica químicamente** si un átomo es realmente `Ce3+`; usa únicamente el criterio de magnetización `|f| > umbral`.
3. `La` se usa solo como **etiqueta de identificación visual**.
4. El archivo generado **no debe usarse directamente para correr VASP** a menos que el resto de los archivos de entrada (`POTCAR`, etc.) sean consistentes con ese cambio de especies.

---

## Recomendación de uso

Primero probar siempre con:

```bash
python contcar_mark_ce3_recursive.py . --dry-run
```

y revisar que:

- los índices detectados son los esperados,
- la nueva línea de especies tiene sentido,
- la nueva línea de conteos coincide con la partición deseada del bloque de Ce.

Después ejecutar en modo normal.

---

## Requisitos

- Python 3
- No requiere librerías externas

---

## Nombre del script

Archivo principal:

```text
contcar_mark_ce3_recursive.py
```

