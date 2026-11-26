"""Genera las ventanas XML de K2: tablero por áreas (A), filas por estancia (C) y panel lateral (B).

Uso: python3 herramientas/generar_ventanas.py
Salen en addon/service.ha_link/resources/skins/Default/1080i/. También genera estuary/include_ha_link_inicio.xml, la
fila de baldosas para la pantalla de inicio de un clon de Estuary (la copia el parche de Estuary Adviser). Medidas de las maquetas (1280×720) por 1,5.
Las imágenes son de herramientas/generar_k2.py; las propiedades de cada ListItem, de resources/lib/ha_link/tablero.py
(las rutas de imagen llegan ya completas desde ventana.py). Fuentes: las de Estuary (y Estuary Adviser).
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(RAIZ, "addon", "service.ha_link")
sys.path.insert(0, os.path.join(ADDON, "resources", "lib"))
from ha_link import tablero as T  # noqa: E402

SALIDA = os.path.join(ADDON, "resources", "skins", "Default", "1080i")
SALIDA_ESTUARY = os.path.join(RAIZ, "estuary", "include_ha_link_inicio.xml")
# En un skin las imágenes propias del addon van con su ruta completa (las de cada ListItem ya llegan completas)
MEDIA_ADDON = "special://home/addons/service.ha_link/resources/skins/Default/media/"

FONDO = "FF0A0E13"
BALDOSA = "FF151B23"
BALDOSA_FOCO = "FF1C232D"
SELECCION = "FF1C2430"
PISTA = "FF27313D"

# ids de los controles (ventana.py los usa)
AREAS, BALDOSAS = 100, 200
FILAS, PRIMERA_FILA = 300, 301
AHORA_1, AHORA_3, AQUI = 400, 402, 401


# --- piezas -----------------------------------------------------------------------------------------
def imagen(x, y, w, h, textura, color=None, visible=None, extra="", borde=None, aspecto=None):
    attrs = ' border="%d"' % borde if borde else ""
    c = "<colordiffuse>%s</colordiffuse>" % color if color else ""
    v = "<visible>%s</visible>" % visible if visible else ""
    a = "<aspectratio>%s</aspectratio>" % aspecto if aspecto else ""
    return ('<control type="image"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
            '<texture%s>%s</texture>%s%s%s%s</control>' % (x, y, w, h, attrs, textura, c, a, v, extra))


def etiqueta(x, y, w, h, texto, fuente, color, alin="left", alin_y="center", visible=None, extra=""):
    v = "<visible>%s</visible>" % visible if visible else ""
    return ('<control type="label"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
            '<font>%s</font><textcolor>%s</textcolor><align>%s</align><aligny>%s</aligny><label>%s</label>'
            '%s%s</control>' % (x, y, w, h, fuente, color, alin, alin_y, texto, v, extra))


def caja(x, y, w, h, texto, fuente, color, visible=None):
    """Texto de hasta dos líneas, abajo del todo (en una lista, una etiqueta no salta de línea; un textbox sí)."""
    v = "<visible>%s</visible>" % visible if visible else ""
    return ('<control type="textbox"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
            '<font>%s</font><textcolor>%s</textcolor><align>left</align><aligny>bottom</aligny><label>%s</label>'
            '<autoscroll>false</autoscroll>%s</control>' % (x, y, w, h, fuente, color, texto, v))


def prop(nombre):
    return "$INFO[ListItem.Property(%s)]" % nombre


def vacio(nombre, item=True):
    return "String.IsEmpty(%s.Property(%s))" % ("ListItem" if item else "Window", nombre)


def igual(nombre, valor):
    return "String.IsEqual(ListItem.Property(%s),%s)" % (nombre, valor)


LATE = '<animation effect="fade" start="100" end="25" time="900" tween="sine" pulse="true" condition="true">Conditional</animation>'


def bloque(x, y, s):
    """Bloque de estado con su halo, anillo de alerta, glifo y marca de «no disponible» (s = lado del bloque)."""
    h = s * 2
    a = int(s * 1.15)
    m = int(s * 0.33)
    g = int(s * 0.5)
    return "".join([
        imagen(x + s // 2 - h // 2, y + s // 2 - h // 2, h, h, prop("halo"), visible="!" + vacio("halo")),
        imagen(x + s // 2 - a // 2, y + s // 2 - a // 2, a, a, "k2/anillo_alerta.png",
               visible="!" + vacio("alerta"), extra=LATE),
        imagen(x, y, s, s, prop("bloque"), visible="!" + vacio("bloque")),
        imagen(x + s // 2 - g // 2, y + s // 2 - g // 2, g, g, prop("glifo"), prop("color_glifo"),
               visible="!" + vacio("bloque")),
        imagen(x + s - m + 6, y + s - m + 6, m, m, "k2/nd_marca.png", visible="!" + vacio("nd")),
    ])


def anillo(x, y, s):
    g = int(s * 0.42)
    return "".join([
        imagen(x, y, s, s, "k2/aro_pista.png", PISTA, visible="!" + vacio("aro")),
        imagen(x, y, s, s, prop("aro"), prop("color_aro"), visible="!" + vacio("aro")),
        imagen(x + s // 2 - g // 2, y + s // 2 - g // 2, g, g, prop("glifo"), prop("color_glifo"),
               visible="!" + vacio("aro")),
    ])


def foco(w, h, contenedor):
    return imagen(0, 0, w, h, "k2/foco.png", "FFFFFFFF", visible="Control.HasFocus(%d)" % contenedor, borde=34)


def zoom(w, h, contenedor, cuanto):
    return ('<animation effect="zoom" start="100" end="%d" center="%d,%d" time="150" tween="cubic" '
            'condition="Control.HasFocus(%d)">Conditional</animation>' % (cuanto, w // 2, h // 2, contenedor))


def tecla(x, y, glifo, texto):
    return "".join([
        imagen(x, y, 45, 45, "k2/circulo.png", "FF1A222C"),
        imagen(x + 11, y + 11, 23, 23, "k2/glifos/%s.png" % glifo, "FFC9D2DC"),
        etiqueta(x + 58, y, 400, 45, texto, "font12", T.SUB),
    ])


def cabecera(ancho=1920, izquierda=72):
    return "".join([
        imagen(izquierda, 40, 48, 48, "k2/glifos/home.png", "FFFFFFFF"),
        etiqueta(izquierda + 66, 30, 400, 66, "$INFO[Window.Property(casa)]", "font40_title", "FFFFFFFF"),
        etiqueta(ancho - izquierda - 300, 30, 300, 66, "$INFO[System.Time]", "font45", "FFFFFFFF", alin="right"),
        imagen(ancho - izquierda - 640, 43, 42, 42, "k2/circulo.png", "26FFFFFF"),
        imagen(ancho - izquierda - 629, 54, 20, 20, "$INFO[Window.Property(estado_glifo)]",
               "$INFO[Window.Property(estado_color)]"),
        etiqueta(ancho - izquierda - 586, 30, 270, 66, "$INFO[Window.Property(estado)]", "font10", T.SUB),
    ])


def ventana(defecto, controles, dialogo=False):
    tipo = ' type="dialog"' if dialogo else ""
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!-- Generado por herramientas/generar_ventanas.py: no editar a mano -->\n'
            '<window%s>\n<defaultcontrol always="true">%d</defaultcontrol>\n<zorder>1</zorder>\n'
            '<controls>\n%s\n</controls>\n</window>\n' % (tipo, defecto, "\n".join(controles)))


# --- baldosas ------------------------------------------------------------------------------------
def baldosa_ancha(w, h, contenedor, enfocada):
    """Baldosa del tablero (A): bloque o aro a la izquierda y dos líneas de texto."""
    s = 120
    bx, by = 30, (h - s) // 2
    tx = bx + s + 27
    tw = w - tx - 21
    cuerpo = [
        imagen(0, 0, w, h, "k2/baldosa.png", BALDOSA_FOCO if enfocada else BALDOSA, borde=34),
        imagen(0, 0, w, h, prop("lavado"), visible="!" + vacio("lavado")),
        bloque(bx, by, s),
        anillo(bx - 3, by - 3, s + 6),
        # estado y escena: nombre arriba, estado (o área) debajo
        caja(tx, by + 2, tw, 80, "$INFO[ListItem.Label]", "font13", T.TXT, visible="!" + igual("clase", "valor")),
        etiqueta(tx, by + 82, tw, 36, "$INFO[ListItem.Label2]", "font10", T.SUB,
                 visible=igual("clase", "estado")),
        imagen(tx, by + 88, 26, 26, "k2/glifos/play.png", T.CIAN, visible=igual("clase", "escena")),
        etiqueta(tx + 32, by + 82, tw - 32, 36, "$INFO[Window.Property(txt_escena)]", "font10", T.SUB,
                 visible=igual("clase", "escena")),
        # valor: número grande con la unidad en gris y el nombre debajo
        etiqueta(tx, by + 6, tw, 70, "%s[COLOR %s] %s[/COLOR]" % (prop("valor"), T.SUB, prop("unidad")),
                 "font45_title", T.TXT, visible=igual("clase", "valor")),
        etiqueta(tx, by + 78, tw, 40, "$INFO[ListItem.Label2]", "font12", T.SUB, visible=igual("clase", "valor")),
    ]
    if enfocada:
        cuerpo.append(foco(w, h, contenedor))
    return '<control type="group">%s%s</control>' % ("".join(cuerpo), zoom(w, h, contenedor, 105) if enfocada else "")


def baldosa_cuadrada(w, h, contenedor, enfocada, s=90):
    """Baldosa cuadrada (filas y panel lateral): bloque arriba a la izquierda y el texto abajo."""
    p = 21
    cuerpo = [
        imagen(0, 0, w, h, "k2/baldosa.png", BALDOSA_FOCO if enfocada else BALDOSA, borde=34),
        imagen(0, 0, w, h, prop("lavado"), visible="!" + vacio("lavado"), aspecto="scale"),
        bloque(p, p, s),
        anillo(p - 2, p - 2, s + 4),
        etiqueta(p, h - 84, w - 2 * p, 40, "$INFO[ListItem.Label]", "font12", T.TXT,
                 visible="!" + igual("clase", "valor")),
        etiqueta(p, h - 46, w - 2 * p, 30, "$INFO[ListItem.Label2]", "font10", T.SUB,
                 visible=igual("clase", "estado")),
        imagen(p, h - 42, 22, 22, "k2/glifos/play.png", T.CIAN, visible=igual("clase", "escena")),
        etiqueta(p + 26, h - 46, w - 2 * p - 26, 30, "$INFO[Window.Property(txt_escena)]", "font10", T.SUB,
                 visible=igual("clase", "escena")),
        etiqueta(p, h - 92, w - 2 * p, 52, "%s[COLOR %s] %s[/COLOR]" % (prop("valor"), T.SUB, prop("unidad")),
                 "font36_title", T.TXT, visible=igual("clase", "valor")),
        etiqueta(p, h - 46, w - 2 * p, 30, "$INFO[ListItem.Label2]", "font10", T.SUB,
                 visible=igual("clase", "valor")),
    ]
    if enfocada:
        cuerpo.append(foco(w, h, contenedor))
    return '<control type="group">%s%s</control>' % ("".join(cuerpo), zoom(w, h, contenedor, 107) if enfocada else "")


# --- indicadores ----------------------------------------------------------------------------------
def indicadores_derecha(fin, y, item=True):
    """Círculos (hasta 3) y temperatura alineados a la derecha, terminando en x = fin."""
    pre = "ListItem" if item else "Window"
    s, paso = 40, 46
    trozos = [etiqueta(fin - 110, y, 110, s, "$INFO[%s.Property(temp)]" % pre, "font12", "FFF1F4F7", alin="right",
                       visible="!String.IsEmpty(%s.Property(temp))" % pre)]
    trozos.append(imagen(fin - 26, y + 7, 26, 26, "k2/glifos/check-circle-outline.png", "66" + T.SUB[2:],
                         visible="!String.IsEmpty(%s.Property(tranquilo))" % pre))
    con_temp = "!String.IsEmpty(%s.Property(temp))" % pre
    for hay_temp in (True, False):
        borde = fin - (118 if hay_temp else 0)
        cond_t = con_temp if hay_temp else "String.IsEmpty(%s.Property(temp))" % pre
        for n in (1, 2, 3):
            for i in range(1, n + 1):
                x = borde - (n - i + 1) * paso
                cond = "%s + String.IsEqual(%s.Property(n_ind),%d)" % (cond_t, pre, n)
                trozos.append(imagen(x, y, s, s, "$INFO[%s.Property(ind%d)]" % (pre, i), visible=cond))
                trozos.append(imagen(x + 9, y + 9, 22, 22, "$INFO[%s.Property(ind%d_glifo)]" % (pre, i),
                                     "$INFO[%s.Property(ind%d_color)]" % (pre, i), visible=cond))
    # termómetro delante de la temperatura
    trozos.insert(0, imagen(fin - 110, y + 6, 28, 28, "k2/glifos/thermometer.png",
                            "$INFO[%s.Property(temp_color)]" % pre, visible=con_temp))
    return "".join(trozos)


# --- A · tablero ----------------------------------------------------------------------------------
def tablero():
    nav_w, fila_h = 450, 90
    gx, gy = 72 + nav_w + 45, 213
    bw, bh, hueco = 409, 225, 27

    def area_item(enfocada):
        cuerpo = []
        if enfocada:
            cuerpo += [imagen(0, 0, nav_w, fila_h, "k2/baldosa.png", SELECCION, borde=34),
                       imagen(0, 21, 6, 48, "k2/barra.png", "FFFFFFFF", visible="Control.HasFocus(%d)" % AREAS)]
        cuerpo += [
            imagen(27, 27, 36, 36, prop("glifo"), "FFFFFFFF" if enfocada else T.SUB),
            _nombre_area(84, fila_h, nav_w - 21, "FFFFFFFF" if enfocada else "FFD5DCE3"),
            indicadores_derecha(nav_w - 21, 25),
        ]
        return "".join(cuerpo)

    controles = [
        imagen(0, 0, 1920, 1080, "k2/blanco.png", FONDO),
        cabecera(),
        ('<control type="list" id="%d"><left>72</left><top>117</top><width>%d</width><height>850</height>'
         '<onright>%d</onright><orientation>vertical</orientation><scrolltime>200</scrolltime>'
         '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s</focusedlayout>'
         '</control>' % (AREAS, nav_w, BALDOSAS, nav_w, fila_h + 9, area_item(False), nav_w, fila_h + 9,
                         area_item(True))),
        etiqueta(gx, 117, 1000, 96, "$INFO[Window.Property(area)]", "font52_title", "FFFFFFFF"),
        ('<control type="panel" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
         '<onleft>%d</onleft><orientation>vertical</orientation><scrolltime>200</scrolltime>'
         '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s</focusedlayout>'
         '</control>' % (BALDOSAS, gx - 12, gy - 12, 3 * (bw + hueco) + 12, 3 * (bh + hueco) + 12, AREAS,
                         bw + hueco, bh + hueco, _con_margen(baldosa_ancha(bw, bh, BALDOSAS, False)),
                         bw + hueco, bh + hueco, _con_margen(baldosa_ancha(bw, bh, BALDOSAS, True)))),
        etiqueta(0, 480, 1920, 120, "$INFO[Window.Property(aviso)]", "font37", T.SUB, alin="center",
                 visible="!String.IsEmpty(Window.Property(aviso))"),
        tecla(72, 1005, "circle-medium", "$INFO[Window.Property(txt_ver)]"),
        tecla(330, 1005, "arrow-left", "$INFO[Window.Property(txt_salir)]"),
    ]
    return ventana(AREAS, controles)


def _con_margen(grupo, m=12):
    """El panel se corre 12 px para que el zoom del foco no se corte: la baldosa vuelve a su sitio."""
    return '<control type="group"><left>%d</left><top>%d</top>%s</control>' % (m, m, grupo)


# --- C · filas -----------------------------------------------------------------------------------------
def filas():
    w = h = 219
    hueco = 24
    alto_fila = 48 + 15 + h + 30
    grupos = []
    for i in range(T.MAX_FILAS):
        ident = PRIMERA_FILA + i
        pre = "fila%d_" % i
        cabeza = ('<control type="grouplist"><left>0</left><top>0</top><width>1776</width><height>48</height>'
                  '<orientation>horizontal</orientation><itemgap>14</itemgap><usecontrolcoords>true</usecontrolcoords>'
                  '%s%s%s%s</control>' % (
                      imagen(0, 6, 36, 36, "$INFO[Window.Property(%sglifo)]" % pre, T.SUB),
                      ('<control type="label"><width>auto</width><height>48</height><font>font36_title</font>'
                       '<textcolor>FFFFFFFF</textcolor><aligny>center</aligny>'
                       '<label>$INFO[Window.Property(%snombre)]</label></control>' % pre),
                      "".join(_indicador_fila(pre, n) for n in (1, 2, 3)),
                      _temp_fila(pre)))
        lista = ('<control type="list" id="%d"><left>-12</left><top>51</top><width>1800</width><height>%d</height>'
                 '<orientation>horizontal</orientation><scrolltime>200</scrolltime><onup>%d</onup><ondown>%d</ondown>'
                 '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s'
                 '</focusedlayout></control>' % (
                     ident, h + 24, ident - 1 if i else ident, ident + 1, w + hueco, h + 24,
                     _con_margen(baldosa_cuadrada(w, h, ident, False)), w + hueco, h + 24,
                     _con_margen(baldosa_cuadrada(w, h, ident, True))))
        grupos.append('<control type="group"><width>1800</width><height>%d</height>'
                      '<visible>!String.IsEmpty(Window.Property(%snombre))</visible>%s%s</control>'
                      % (alto_fila, pre, cabeza, lista))
    controles = [
        imagen(0, 0, 1920, 1080, "k2/blanco.png", FONDO),
        cabecera(),
        ('<control type="grouplist" id="%d"><left>72</left><top>132</top><width>1800</width><height>948</height>'
         '<orientation>vertical</orientation><itemgap>0</itemgap><scrolltime>250</scrolltime>%s</control>'
         % (FILAS, "".join(grupos))),
        etiqueta(0, 480, 1920, 120, "$INFO[Window.Property(aviso)]", "font37", T.SUB, alin="center",
                 visible="!String.IsEmpty(Window.Property(aviso))"),
    ]
    return ventana(PRIMERA_FILA, controles)


def _nombre_area(x, alto, fin, color):
    """Nombre del área en el tablero: tan ancho como dejen los indicadores de su derecha (cuántos círculos hay y si
    hay temperatura), para que no se monte sobre ellos. Las medidas salen de indicadores_derecha."""
    trozos = []
    for hay_temp in (True, False):
        cond_t = "%sString.IsEmpty(ListItem.Property(temp))" % ("!" if hay_temp else "")
        for n in (0, 1, 2, 3):
            if n:
                inicio = fin - (118 if hay_temp else 0) - n * 46
            else:
                inicio = fin - 110 if hay_temp else fin - 26  # termómetro, o la marca de «en reposo»
            ancho = min(230, inicio - x - 8)
            cond = "%s + String.IsEqual(ListItem.Property(n_ind),%d)" % (cond_t, n)
            trozos.append(etiqueta(x, 0, ancho, alto, "$INFO[ListItem.Label]", "font27", color, visible=cond))
    return "".join(trozos)


def _indicador_fila(pre, i):
    cond = "!String.IsEmpty(Window.Property(%sind%d))" % (pre, i)
    return ('<control type="group"><width>40</width><height>48</height><visible>%s</visible>%s%s</control>'
            % (cond, imagen(0, 4, 40, 40, "$INFO[Window.Property(%sind%d)]" % (pre, i)),
               imagen(9, 13, 22, 22, "$INFO[Window.Property(%sind%d_glifo)]" % (pre, i),
                      "$INFO[Window.Property(%sind%d_color)]" % (pre, i))))


def _temp_fila(pre):
    cond = "!String.IsEmpty(Window.Property(%stemp))" % pre
    return ('<control type="group"><width>120</width><height>48</height><visible>%s</visible>%s%s</control>'
            % (cond, imagen(0, 10, 28, 28, "k2/glifos/thermometer.png", "$INFO[Window.Property(%stemp_color)]" % pre),
               etiqueta(30, 0, 90, 48, "$INFO[Window.Property(%stemp)]" % pre, "font12", "FFF1F4F7")))


# --- B · panel lateral -------------------------------------------------------------------------------
def lateral():
    ancho = 705
    x0 = 1920 - ancho
    p = 42
    w, h, hueco = 195, 204, 18

    def panel(ident, top, filas_n, arriba, abajo, visible):
        return ('<control type="panel" id="%d"><left>%d</left><top>%d</top><width>%d</width><height>%d</height>'
                '<onup>%d</onup><ondown>%d</ondown><orientation>vertical</orientation><scrolltime>200</scrolltime>'
                '<visible>%s</visible>'
                '<itemlayout width="%d" height="%d">%s</itemlayout><focusedlayout width="%d" height="%d">%s'
                '</focusedlayout></control>' % (
                    ident, x0 + p - 12, top - 12, 3 * (w + hueco) + 12, filas_n * (h + hueco) + 12, arriba, abajo,
                    visible, w + hueco, h + hueco, _con_margen(baldosa_cuadrada(w, h, ident, False, 84)),
                    w + hueco, h + hueco, _con_margen(baldosa_cuadrada(w, h, ident, True, 84))))

    def titulo(y, prop_ventana, visible=None):
        return etiqueta(x0 + p, y, ancho - 2 * p, 36, "$INFO[Window.Property(%s)]" % prop_ventana, "font12",
                        "FF8A96A3", visible=visible)

    con_aqui = "!String.IsEmpty(Window.Property(aqui))"
    controles = [
        imagen(x0, 0, ancho, 1080, "k2/blanco.png", "ED0A0E13"),
        imagen(x0 + p, 48, 42, 42, "k2/glifos/home.png", "FFFFFFFF"),
        etiqueta(x0 + p + 58, 36, 300, 66, "$INFO[Window.Property(casa)]", "font36_title", "FFFFFFFF"),
        etiqueta(1920 - p - 260, 36, 260, 66, "$INFO[System.Time]", "font36_title", "FFFFFFFF", alin="right"),
        titulo(126, "txt_ahora"),
        panel(AHORA_1, 168, 1, AHORA_1, AQUI, con_aqui),
        panel(AHORA_3, 168, 3, AHORA_3, AHORA_3, "!" + con_aqui),
        imagen(x0 + p, 178, 36, 36, "k2/glifos/check-circle-outline.png", "99" + T.SUB[2:],
               visible="!String.IsEmpty(Window.Property(tranquilo))"),
        etiqueta(x0 + p + 50, 172, ancho - 2 * p - 50, 48, "$INFO[Window.Property(tranquilo)]", "font12", T.SUB,
                 visible="!String.IsEmpty(Window.Property(tranquilo))"),
        titulo(402, "aqui", visible=con_aqui),
        panel(AQUI, 444, 2, AHORA_1, AQUI, con_aqui),
        etiqueta(x0 + p, 480, ancho - 2 * p, 120, "$INFO[Window.Property(aviso)]", "font27", T.SUB, alin="center",
                 visible="!String.IsEmpty(Window.Property(aviso))"),
        tecla(x0 + p, 1002, "circle-medium", "$INFO[Window.Property(txt_ver)]"),
        tecla(x0 + p + 210, 1002, "arrow-left", "$INFO[Window.Property(txt_volver)]"),
    ]
    return ventana(AHORA_1, controles, dialogo=True)


# --- pantalla de inicio de Estuary ---------------------------------------------------------------------
def estuary():
    """Include «HaLinkFila» para Includes_Home.xml de un clon de Estuary: cabecera, spinner y una fila horizontal de
    baldosas cuadradas de K2 con el contenido de plugin://service.ha_link/?fila=... (se pasa en content_path).

    Piezas de Estuary (CategoryLabel, WidgetListCommon) para que encaje en su rejilla; la baldosa es la de las filas
    de K2 (§7.1 del diseño). La lista no se oculta cuando está vacía, como las de Estuary: Kodi no recarga una lista
    oculta, y una fila que arranca vacía (antes de que llegue HA) se quedaría así. Lo que la oculta es `visible`."""
    w = h = 219
    hueco = 24
    marcador = 987654  # se sustituye por el id de la lista, que en un include es un parámetro

    def capa(enfocada):
        xml = _con_margen(baldosa_cuadrada(w, h, marcador, enfocada))
        xml = xml.replace(str(marcador), "$PARAM[list_id]").replace(">k2/", ">" + MEDIA_ADDON + "k2/")
        # en la ventana Home no están los textos que pone ventana.py: se leen del addon
        return xml.replace("$INFO[Window.Property(txt_escena)]", "$ADDON[service.ha_link %d]" % T.IDS["escena"])

    return """<?xml version="1.0" encoding="UTF-8"?>
<!-- Generado por kodi-addon-ha-link/herramientas/generar_ventanas.py: no editar a mano -->
<include name="HaLinkFila">
	<param name="visible">true</param>
	<definition>
		<include content="CategoryLabel">
			<param name="label">$PARAM[widget_header]</param>
			<param name="list_id" value="$PARAM[list_id]"/>
			<param name="visible" value="$PARAM[visible]"/>
		</include>
		<include content="BusyListSpinner">
			<param name="list_id" value="$PARAM[list_id]"/>
			<param name="visible" value="$PARAM[visible]"/>
		</include>
		<control type="panel" id="$PARAM[list_id]">
			<left>58</left>
			<top>110</top>
			<right>0</right>
			<height>330</height>
			<include content="WidgetListCommon">
				<param name="list_id" value="$PARAM[list_id]"/>
			</include>
			<visible>$PARAM[visible]</visible>
			<itemlayout width="%(iw)d" height="%(ih)d">%(normal)s</itemlayout>
			<focusedlayout width="%(iw)d" height="%(ih)d">%(foco)s</focusedlayout>
			<content target="programs">$PARAM[content_path]</content>
		</control>
	</definition>
</include>
""" % {"iw": w + hueco, "ih": h + hueco, "normal": capa(False), "foco": capa(True)}


def main():
    os.makedirs(os.path.dirname(SALIDA_ESTUARY), exist_ok=True)
    with open(SALIDA_ESTUARY, "w", encoding="utf-8") as f:
        f.write(estuary())
    os.makedirs(SALIDA, exist_ok=True)
    for nombre, xml in (("ha_link_tablero.xml", tablero()), ("ha_link_filas.xml", filas()),
                        ("ha_link_lateral.xml", lateral())):
        with open(os.path.join(SALIDA, nombre), "w", encoding="utf-8") as f:
            f.write(xml)
    print("ventanas en %s" % SALIDA)


if __name__ == "__main__":
    main()
