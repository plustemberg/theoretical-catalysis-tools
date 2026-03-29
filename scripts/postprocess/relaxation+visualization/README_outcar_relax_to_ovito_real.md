# `outcar_relax_to_ovito_real.py`

Script para extraer una relajación iónica desde un `OUTCAR` de VASP y generar, en una sola corrida:

- una trayectoria multiframe en formato `extxyz` para abrir en **OVITO**
- un archivo `.csv` resumen con energías, fuerzas y magnetización
- un gráfico de **energía relativa** vs iteración iónica
- un gráfico de **fuerza máxima atómica** vs iteración iónica
- un gráfico de **magnetización total** vs iteración iónica, si el `OUTCAR` contiene esa información
- cuatro vistas PNG de la estructura final renderizadas con **OVITO real**:
  - `xy` (top)
  - `xz` (front)
  - `yz` (right)
  - `iso` (oblicua)

El script funciona con:

- un fichero `OUTCAR`
- una carpeta de cálculo que contenga `OUTCAR`
- una carpeta raíz, usando modo recursivo para procesar todos los subdirectorios que contengan `OUTCAR`

---

## 1. Qué hace exactamente

### Desde el `OUTCAR`

El script busca todos los bloques iónicos `POSITION ... TOTAL-FORCE`, y para cada paso extrae:

- posiciones atómicas
- fuerzas cartesianas
- energía total (`TOTEN`)
- magnetización total, cuando aparece en el `OUTCAR`
- celda periódica, si está disponible en el `OUTCAR`

### Archivos que genera

Por defecto el prefijo de salida es:

```text
relax
```

Por tanto, en una carpeta de cálculo genera normalmente:

```text
relax.extxyz
relax_summary.csv
relax_energy.png
relax_forces.png
relax_magnetization.png   # solo si hay magnetización
relax_view_xy.png
relax_view_xz.png
relax_view_yz.png
relax_view_iso.png
```

### Referencia de energía

El gráfico de energías y el CSV usan:

```text
ΔE = E(i) - E(1)
```

Es decir:

- el primer paso vale `0`
- en una relajación normal, los últimos pasos suelen ser negativos respecto al primero

### Estructura usada para los PNG

Para las vistas renderizadas con OVITO, el script intenta usar, por este orden:

1. `CONTCAR`
2. `POSCAR`
3. el último frame extraído del `OUTCAR`

Esto permite seguir generando PNG aunque no haya `CONTCAR`.

---

## 2. Requisitos

### Python

El script está pensado para Python 3 en Linux/WSL.

### Paquetes Python necesarios

- `numpy`
- `matplotlib`
- `ovito`

Instalación típica dentro de tu entorno virtual:

```bash
source ~/venvs/ase-env/bin/activate
python -m pip install -U pip
pip install -U numpy matplotlib ovito
```

### Librerías del sistema en Ubuntu / WSL

Para que `import ovito` funcione en WSL/Ubuntu, además del paquete Python suelen hacer falta librerías OpenGL/EGL del sistema.

En Ubuntu reciente, instala:

```bash
sudo apt update
sudo apt install -y libopengl0 libegl1 libgl1 libglx-mesa0
```

Después comprueba:

```bash
source ~/venvs/ase-env/bin/activate
python -c "import ovito; print('OVITO OK')"
```

Si aparece `OVITO OK`, el entorno ya está listo.

---

## 3. Uso básico

### Caso 1: pasar directamente un `OUTCAR`

```bash
python outcar_relax_to_ovito_real.py OUTCAR
```

### Caso 2: pasar una carpeta de cálculo

```bash
python outcar_relax_to_ovito_real.py .
```

El script buscará:

```text
./OUTCAR
```

### Caso 3: usar un prefijo personalizado

```bash
python outcar_relax_to_ovito_real.py OUTCAR -o ni607_relax
```

Esto generará:

```text
ni607_relax.extxyz
ni607_relax_summary.csv
ni607_relax_energy.png
...
```

---

## 4. Uso recursivo

Para procesar todos los subdirectorios bajo una carpeta raíz que contengan un `OUTCAR`:

```bash
python outcar_relax_to_ovito_real.py /ruta/raiz --recursive
```

O desde la carpeta actual:

```bash
python outcar_relax_to_ovito_real.py . --recursive
```

En modo recursivo:

- el script busca todos los `OUTCAR`
- cada cálculo se procesa en su propia carpeta
- el prefijo usado es `relax`
- en pantalla se muestra una línea por cálculo, por ejemplo:

```text
[OK] /ruta/al/OUTCAR -> /ruta/al/relax
```

---

## 5. Opciones disponibles

### `-o`, `--output-prefix`

Permite cambiar el prefijo de salida en modo no recursivo.

Ejemplo:

```bash
python outcar_relax_to_ovito_real.py OUTCAR -o mi_relajacion
```

### `--recursive`

Procesa recursivamente todos los subdirectorios con `OUTCAR`.

Ejemplo:

```bash
python outcar_relax_to_ovito_real.py . --recursive
```

### `--atom-scale`

Escala global del tamaño de las esferas en los PNG generados con OVITO.

Valor por defecto:

```text
1.20
```

Ejemplo:

```bash
python outcar_relax_to_ovito_real.py OUTCAR --atom-scale 1.35
```

Si quieres que las esferas llenen más los huecos, aumenta este valor.

### `--renderer`

Motor de render de OVITO.

Opciones disponibles:

- `opengl`  
- `tachyon`

Por defecto:

```text
opengl
```

Ejemplos:

```bash
python outcar_relax_to_ovito_real.py OUTCAR --renderer opengl
python outcar_relax_to_ovito_real.py OUTCAR --renderer tachyon
```

### `--use-custom-colors`

Usa el diccionario `CUSTOM_ELEMENT_COLORS` definido en el script en lugar de los colores por defecto de OVITO.

Ejemplo:

```bash
python outcar_relax_to_ovito_real.py OUTCAR --use-custom-colors
```

---

## 6. Colores personalizados

En la parte superior del script existe este diccionario:

```python
CUSTOM_ELEMENT_COLORS = {
    # 'Ce': (0.94, 0.91, 0.69),
    # 'O':  (1.00, 0.00, 0.00),
    # 'Ni': (0.00, 0.28, 1.00),
    # 'C':  (0.75, 0.75, 0.75),
    # 'H':  (1.00, 1.00, 1.00),
}
```

### Cómo usarlo

1. Edita el script y descomenta o añade los elementos que quieras.
2. Ejecuta el script con:

```bash
python outcar_relax_to_ovito_real.py OUTCAR --use-custom-colors
```

### Ejemplo

```python
CUSTOM_ELEMENT_COLORS = {
    'Ce': (1.00, 1.00, 1.00),
    'O':  (1.00, 0.00, 0.00),
    'Ni': (0.00, 0.00, 1.00),
    'C':  (0.70, 0.70, 0.70),
    'H':  (0.95, 0.95, 0.95),
}
```

Si **no** usas `--use-custom-colors`, OVITO empleará sus colores por defecto según el nombre del elemento.

---

## 7. Salida por pantalla

En modo no recursivo, al terminar la corrida el script imprime un resumen del tipo:

```text
Directory               : /ruta/al/calculo
OUTCAR                  : /ruta/al/calculo/OUTCAR
Frames extracted        : 173
Atoms per frame         : 114
Output prefix           : /ruta/al/calculo/relax
Views generated from    : CONTCAR
Wrote                   : /ruta/al/calculo/relax.extxyz
Wrote                   : /ruta/al/calculo/relax_summary.csv
Wrote                   : /ruta/al/calculo/relax_energy.png
Wrote                   : /ruta/al/calculo/relax_forces.png
Wrote                   : /ruta/al/calculo/relax_magnetization.png
Wrote                   : /ruta/al/calculo/relax_view_xy.png
Wrote                   : /ruta/al/calculo/relax_view_xz.png
Wrote                   : /ruta/al/calculo/relax_view_yz.png
Wrote                   : /ruta/al/calculo/relax_view_iso.png
```

---

## 8. Formato del CSV

El archivo `*_summary.csv` contiene las columnas:

```text
step
energy_eV
deltaE_vs_first_eV
max_force_eVA
rms_force_eVA
total_magnetization
```

### Significado

- `step`: número de iteración iónica
- `energy_eV`: energía total del paso
- `deltaE_vs_first_eV`: energía relativa respecto al primer paso
- `max_force_eVA`: fuerza atómica máxima del paso
- `rms_force_eVA`: fuerza RMS del paso
- `total_magnetization`: magnetización total, si existe en el `OUTCAR`

---

## 9. Trayectoria `extxyz`

El archivo `relax.extxyz` contiene todos los pasos iónicos y puede abrirse directamente en OVITO.

Cada frame incluye:

- especie química
- posición cartesiana
- fuerzas
- metadatos globales como:
  - `step`
  - `energy`
  - `delta_e`
  - `max_force`
  - `magnetization` cuando está disponible

### Abrir en OVITO

Desde la GUI de OVITO:

- `File -> Load File`
- selecciona `relax.extxyz`

Podrás recorrer toda la relajación frame a frame.

---

## 10. Interpretación de las vistas PNG

Los archivos:

```text
relax_view_xy.png
relax_view_xz.png
relax_view_yz.png
relax_view_iso.png
```

corresponden a:

- `xy`: vista superior
- `xz`: vista frontal
- `yz`: vista lateral
- `iso`: vista oblicua ortográfica

### Estilo visual

- render real con OVITO
- fondo blanco
- sin bonds añadidos por el script
- celda visible en gris
- tamaño de esfera controlado por `--atom-scale`

---

## 11. Ejemplos completos

### Ejemplo 1: correr dentro de la carpeta del cálculo

```bash
cd /mnt/c/Trabajo/00_DATOS/GOFEE/NiOx/R2SCAN/CH4ads/Ni607/3/res1
source ~/venvs/ase-env/bin/activate
python /mnt/c/Trabajo/05_SCRIPTS/scripts/outcar_relax_to_ovito_real.py OUTCAR
```

### Ejemplo 2: usar un prefijo personalizado

```bash
python /mnt/c/Trabajo/05_SCRIPTS/scripts/outcar_relax_to_ovito_real.py OUTCAR -o ni607_ch4_relax
```

### Ejemplo 3: esferas más grandes

```bash
python /mnt/c/Trabajo/05_SCRIPTS/scripts/outcar_relax_to_ovito_real.py OUTCAR --atom-scale 1.35
```

### Ejemplo 4: usar colores personalizados

```bash
python /mnt/c/Trabajo/05_SCRIPTS/scripts/outcar_relax_to_ovito_real.py OUTCAR --use-custom-colors
```

### Ejemplo 5: modo recursivo

```bash
python /mnt/c/Trabajo/05_SCRIPTS/scripts/outcar_relax_to_ovito_real.py /mnt/c/Trabajo/00_DATOS/GOFEE/NiOx --recursive
```

---

## 12. Advertencias y comportamiento esperable en WSL

Durante el render con OVITO en WSL pueden aparecer mensajes tipo:

```text
libEGL warning: ...
MESA: error: ZINK: failed to choose pdev
```

Si aun así el script imprime líneas `Wrote : ...png` y los PNG se generan correctamente, esos mensajes son solo advertencias del backend gráfico de WSL/MESA y no impiden el funcionamiento del script.

Solo debes preocuparte si:

- los PNG salen en blanco
- el script se detiene antes de escribir los archivos
- OVITO da un error fatal y termina la ejecución

---

## 13. Limitaciones actuales

- En modo archivo, el nombre del fichero debe ser exactamente `OUTCAR`.
- El script espera encontrar bloques estándar `POSITION ... TOTAL-FORCE` en el `OUTCAR`.
- Si el `OUTCAR` no contiene metadatos suficientes de especies, el script puede asignar nombres genéricos `X` a los átomos en la trayectoria.
- La magnetización solo se grafica si el `OUTCAR` contiene la información correspondiente.
- El estilo final de los PNG depende del motor de render de OVITO y de tu entorno gráfico en WSL.

---

## 14. Solución de problemas

### Problema: `ImportError: libOpenGL.so.0`

Instala las librerías del sistema:

```bash
sudo apt update
sudo apt install -y libopengl0 libegl1 libgl1 libglx-mesa0
```

### Problema: `python ... no hace nada`

Comprueba que:

- estás ejecutando la versión correcta del script
- estás en el entorno virtual correcto
- existe un `OUTCAR` real en esa carpeta

Ejemplo correcto:

```bash
source ~/venvs/ase-env/bin/activate
python /mnt/c/Trabajo/05_SCRIPTS/scripts/outcar_relax_to_ovito_real.py OUTCAR
```

### Problema: no aparece `relax_magnetization.png`

Eso normalmente significa que el `OUTCAR` no contiene magnetización total parseable por el script.

### Problema: las esferas se ven pequeñas

Aumenta el parámetro:

```bash
--atom-scale
```

Por ejemplo:

```bash
python outcar_relax_to_ovito_real.py OUTCAR --atom-scale 1.35
```

### Problema: quiero otros colores

Edita `CUSTOM_ELEMENT_COLORS` y usa:

```bash
--use-custom-colors
```

---

## 15. Recomendación de uso

Flujo recomendado:

1. Corre el script en la carpeta del cálculo.
2. Revisa el gráfico de energía para confirmar que la relajación converge hacia energías más bajas.
3. Revisa el gráfico de fuerzas para evaluar la convergencia geométrica.
4. Revisa la magnetización si el cálculo es spin-polarized.
5. Abre `relax.extxyz` en OVITO para inspeccionar toda la trayectoria.
6. Usa los PNG de las vistas finales para documentación rápida o figuras de trabajo.

---

## 16. Nombre del script

Este README corresponde al script:

```text
outcar_relax_to_ovito_real.py
```

Si renombraste el archivo en tu carpeta de scripts, adapta los ejemplos de ejecución al nombre real que estés usando.
