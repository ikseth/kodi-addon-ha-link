"""Genera las imágenes de la ventana propia (K2): glifos blancos, bloques de estado, halos, aros y fondos.

Uso: python3 herramientas/generar_k2.py <carpeta con los SVG de @mdi/svg 7.4.47>
Los SVG se descargan de https://cdn.jsdelivr.net/npm/@mdi/svg@7.4.47/svg/<nombre>.svg. Necesita Inkscape 1.x.
Lenguaje visual en docs/diseno.md §7.1; medidas de las maquetas (1280×720) por 1,5 (la ventana es 1080i).
Los glifos y lo que lleva color variable salen en blanco: Kodi los tiñe con colordiffuse.
"""
import math
import os
import re
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(RAIZ, "addon", "service.ha_link")
sys.path.insert(0, os.path.join(ADDON, "resources", "lib"))
from ha_link import glifos  # noqa: E402
from ha_link.tablero import PASOS_ARO  # noqa: E402

SALIDA = os.path.join(ADDON, "resources", "skins", "Default", "media", "k2")
FONDO = "#0A0E13"


def _svg(w, h, cuerpo, defs=""):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'
            '<defs>%s</defs>%s</svg>' % (w, h, w, h, defs, cuerpo))


def _cuadrado(s, radio, relleno, extra=""):
    return '<rect x="0" y="0" width="%d" height="%d" rx="%g" fill="%s" %s/>' % (s, s, radio, relleno, extra)


def _degradado(ident, a, b):
    # 150° de CSS: de arriba a la izquierda hacia abajo a la derecha
    return ('<linearGradient id="%s" x1="0.25" y1="0" x2="0.75" y2="1">'
            '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>' % (ident, a, b))


def _radial(ident, color, opacidad, cx="0.5", cy="0.5", r="0.5"):
    return ('<radialGradient id="%s" cx="%s" cy="%s" r="%s">'
            '<stop offset="0" stop-color="%s" stop-opacity="%g"/>'
            '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>' % (ident, cx, cy, r, color,
                                                                                     opacidad, color))


def _arco(s, ancho, fraccion):
    """Arco de 270° abierto por abajo (empieza abajo a la izquierda), en blanco, de 0 a fraccion."""
    r = (s - ancho) / 2.0
    c = 2 * math.pi * r
    largo = 0.75 * c
    if fraccion <= 0:
        return ""
    return ('<circle cx="%g" cy="%g" r="%g" fill="none" stroke="#FFFFFF" stroke-width="%g" stroke-linecap="round" '
            'stroke-dasharray="%.2f %.2f" transform="rotate(135 %g %g)"/>'
            % (s / 2.0, s / 2.0, r, ancho, fraccion * largo, c, s / 2.0, s / 2.0))


def _glifo(d, s, color="#FFFFFF", escala=1.0):
    k = escala * s / 24.0
    desp = (s - 24 * k) / 2.0
    return '<path transform="translate(%g %g) scale(%g)" fill="%s" d="%s"/>' % (desp, desp, k, color, d)


def ruta(origen, nombre):
    texto = open(os.path.join(origen, nombre + ".svg"), encoding="utf-8").read()
    m = re.search(r' d="([^"]+)"', texto)
    if not m:
        raise SystemExit("Sin path en %s.svg" % nombre)
    return m.group(1)


def imagenes(origen):
    """{ruta relativa del PNG: svg}."""
    salida = {}
    for nombre in glifos.todos():
        salida["glifos/%s.png" % nombre] = _svg(128, 128, _glifo(ruta(origen, nombre), 128))

    s = 160
    r = s * 0.3
    salida["bloque_activo.png"] = _svg(s, s, _cuadrado(s, r, "url(#g)"), _degradado("g", "#FFCB6B", "#FF9A2E"))
    salida["bloque_alerta.png"] = _svg(s, s, _cuadrado(s, r, "url(#g)"), _degradado("g", "#FF7068", "#E53935"))
    salida["bloque_reposo.png"] = _svg(s, s, _cuadrado(s, r, "#2A3442"))
    salida["bloque_nd.png"] = _svg(s, s, _cuadrado(s, r, "#151A21") + '<rect x="1.5" y="1.5" width="%g" height="%g" '
                                   'rx="%g" fill="none" stroke="#262E38" stroke-width="3"/>' % (s - 3, s - 3, r - 1.5))
    salida["bloque_escena.png"] = _svg(s, s, _cuadrado(s, r, "#4FC3F7", 'fill-opacity="0.13"') + (
        '<rect x="1.5" y="1.5" width="%g" height="%g" rx="%g" fill="none" stroke="#4FC3F7" stroke-opacity="0.45" '
        'stroke-width="3"/>' % (s - 3, s - 3, r - 1.5)))
    # anillo de la alerta, algo mayor que el bloque (late con una animación de la ventana)
    a = 184
    salida["anillo_alerta.png"] = _svg(a, a, '<rect x="5" y="5" width="%g" height="%g" rx="%g" fill="none" '
                                       'stroke="#FF5A52" stroke-opacity="0.32" stroke-width="10"/>'
                                       % (a - 10, a - 10, r + 7))
    h = 320
    salida["halo_activo.png"] = _svg(h, h, '<rect width="%d" height="%d" fill="url(#h)"/>' % (h, h),
                                     _radial("h", "#FFA032", 0.5))
    salida["halo_alerta.png"] = _svg(h, h, '<rect width="%d" height="%d" fill="url(#h)"/>' % (h, h),
                                     _radial("h", "#FF5046", 0.62))
    # lavado de la baldosa: luz suave desde el bloque (a la izquierda)
    salida["lavado_activo.png"] = _svg(420, 225, '<rect width="420" height="225" fill="url(#h)"/>',
                                       _radial("h", "#FFA032", 0.20, cx="0.22", cy="0.5", r="0.62"))
    salida["lavado_alerta.png"] = _svg(420, 225, '<rect width="420" height="225" fill="url(#h)"/>',
                                       _radial("h", "#FF5046", 0.26, cx="0.22", cy="0.5", r="0.66"))
    # círculos de los indicadores de área
    c = 64
    salida["circulo_activo.png"] = _svg(c, c, '<circle cx="32" cy="32" r="32" fill="url(#g)"/>',
                                        _degradado("g", "#FFCB6B", "#FF9A2E"))
    salida["circulo_alerta.png"] = _svg(c, c, '<circle cx="32" cy="32" r="32" fill="url(#g)"/>',
                                        _degradado("g", "#FF7068", "#E53935"))
    salida["circulo.png"] = _svg(c, c, '<circle cx="32" cy="32" r="32" fill="#FFFFFF"/>')
    # baldosa y foco: rectángulos redondeados blancos que Kodi estira con border (9 partes)
    salida["baldosa.png"] = _svg(96, 96, '<rect width="96" height="96" rx="33" fill="#FFFFFF"/>')
    salida["foco.png"] = _svg(96, 96, '<rect x="2.25" y="2.25" width="91.5" height="91.5" rx="31" fill="none" '
                                      'stroke="#FFFFFF" stroke-width="4.5"/>')
    salida["pastilla.png"] = _svg(96, 96, '<rect width="96" height="96" rx="21" fill="#FFFFFF"/>')
    salida["barra.png"] = _svg(12, 48, '<rect width="12" height="48" rx="6" fill="#FFFFFF"/>')
    salida["blanco.png"] = _svg(16, 16, '<rect width="16" height="16" fill="#FFFFFF"/>')
    salida["sombra.png"] = _svg(160, 160, '<rect width="160" height="160" fill="url(#h)"/>',
                                _radial("h", "#000000", 0.55))
    # marca de «no disponible»
    m = 52
    salida["nd_marca.png"] = _svg(m, m, '<circle cx="26" cy="26" r="26" fill="%s"/><circle cx="26" cy="26" r="20" '
                                        'fill="#2A323D"/>%s' % (FONDO, _glifo(ruta(origen, "lan-disconnect"), m,
                                                                               "#9AA6B2", 0.48)))
    # aros: pista y un arco por tramo
    s = 192
    w = 16
    salida["aro_pista.png"] = _svg(s, s, _arco(s, w, 1.0))
    for i in range(PASOS_ARO + 1):
        salida["aro_%02d.png" % i] = _svg(s, s, _arco(s, w, i / float(PASOS_ARO)))
    return salida


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    todas = imagenes(sys.argv[1])
    ordenes = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (nombre, svg) in enumerate(sorted(todas.items())):
            destino = os.path.join(SALIDA, nombre)
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            fuente = os.path.join(tmp, "%04d.svg" % i)
            with open(fuente, "w", encoding="utf-8") as f:
                f.write(svg)
            ordenes.append("file-open:%s; export-filename:%s; export-area-page; export-background-opacity:0; export-do; file-close"
                           % (fuente, destino))
        subprocess.run(["inkscape", "--shell"], input="\n".join(ordenes) + "\nquit\n", text=True, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("%d imágenes en %s" % (len(ordenes), SALIDA))


if __name__ == "__main__":
    main()
