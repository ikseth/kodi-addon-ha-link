"""Genera los iconos del listado: un PNG por tipo y tono, con el glifo de Material Design Icons.

Uso: python3 herramientas/generar_iconos.py <carpeta con los SVG de @mdi/svg 7.4.47>
Los SVG se descargan de https://cdn.jsdelivr.net/npm/@mdi/svg@7.4.47/svg/<nombre>.svg
(licencia en addon/service.ha_link/resources/media/iconos/LICENSE-MDI.txt). Necesita Inkscape 1.x.
"""
import os
import re
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(RAIZ, "addon", "service.ha_link")
sys.path.insert(0, os.path.join(ADDON, "resources", "lib"))
from ha_link import listado  # noqa: E402
from ha_link.glifos import GLIFOS, glifo  # noqa: E402

SALIDA = os.path.join(ADDON, "resources", "media", "iconos")
TAM = 128

def ruta_svg(origen, nombre):
    texto = open(os.path.join(origen, nombre + ".svg"), encoding="utf-8").read()
    m = re.search(r'<path d="([^"]+)"', texto)
    if not m:
        raise SystemExit("Sin path en %s.svg" % nombre)
    return m.group(1)


def svg(d, argb):
    color = "#" + argb[2:]
    escala = 0.62 * TAM / 24.0
    desp = (TAM - 24 * escala) / 2.0
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
            '<circle cx="%g" cy="%g" r="%g" fill="%s" fill-opacity="0.16"/>'
            '<circle cx="%g" cy="%g" r="%g" fill="none" stroke="%s" stroke-opacity="0.45" stroke-width="2.5"/>'
            '<path transform="translate(%g %g) scale(%g)" fill="%s" d="%s"/></svg>'
            % (TAM, TAM, TAM, TAM, TAM / 2, TAM / 2, TAM / 2 - 2, color, TAM / 2, TAM / 2, TAM / 2 - 3, color,
               desp, desp, escala, color, d))


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    origen = sys.argv[1]
    tipos = set(listado.TIPOS.values()) | {"generico", "area", "ahora", "sin_conexion", "espera"}
    faltan = tipos - set(GLIFOS)
    if faltan:
        raise SystemExit("Tipos sin glifo: %s" % sorted(faltan))
    os.makedirs(SALIDA, exist_ok=True)
    ordenes = []
    with tempfile.TemporaryDirectory() as tmp:
        for tipo in sorted(tipos):
            for tono, argb in listado.COLORES.items():
                nombre = glifo(tipo, tono)
                fuente = os.path.join(tmp, "%s_%s.svg" % (tipo, tono))
                with open(fuente, "w", encoding="utf-8") as f:
                    f.write(svg(ruta_svg(origen, nombre), argb))
                destino = os.path.join(SALIDA, "%s_%s.png" % (tipo, tono))
                ordenes.append("file-open:%s; export-filename:%s; export-do; file-close" % (fuente, destino))
        subprocess.run(["inkscape", "--shell"], input="\n".join(ordenes) + "\nquit\n", text=True, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("%d iconos en %s" % (len(ordenes), SALIDA))


if __name__ == "__main__":
    main()
