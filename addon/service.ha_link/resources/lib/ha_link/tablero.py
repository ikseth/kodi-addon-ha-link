"""Modelo de la ventana propia (K2): tablero por áreas (A), filas por estancia (C) y panel lateral (B). Sin xbmc.

ventana.py convierte cada Baldosa o Area en un ListItem: las claves de `props` son propiedades del ListItem que
leen las ventanas XML (resources/skins/Default/1080i/). Lenguaje visual en docs/diseno.md §7.1: el estado lo dice
el icono (bloque, forma del glifo, halo, aro); el texto, en gris, solo lo confirma.
"""
import re
import time

from . import glifos
from . import listado
from . import receptor as R

PASOS_ARO = 20  # aro_00.png … aro_20.png

# Colores de Kodi (AARRGGBB)
TXT = "FFF1F4F7"
SUB = "FF8B97A4"
CIAN = "FF4FC3F7"
AMARILLO = "FFFFD54F"
GLIFO = {"activo": "FF2B1700", "alerta": "FFFFFFFF", "normal": "FF8692A0", "nd": "FF48535F", "escena": CIAN}
BLOQUE = {"activo": "bloque_activo.png", "alerta": "bloque_alerta.png", "normal": "bloque_reposo.png",
          "nd": "bloque_nd.png", "escena": "bloque_escena.png"}

AHORA = listado.AHORA
SIN_AREA = listado.SIN_AREA
MAX_AHORA_LATERAL = 3
MAX_AQUI_LATERAL = 6
MAX_FILAS = 16  # filas que tiene la ventana C (incluida «Ahora mismo»)
MAX_INDICADORES = 3

ESCENAS = ("scene", "script", "button", "input_button")

# Textos (es). Las claves llevan los ids de strings.po a partir de 32100.
TEXTOS = {
    "casa": "Casa",
    "al_dia": "Al día",
    "caducado": "Datos de las {}",
    "esperando": "Esperando a Home Assistant",
    "nada": "No hay nada expuesto para este Kodi",
    "ahora": "Ahora mismo",
    "sin_area": "Sin área",
    "tranquilo": "Todo en reposo",
    "escena": "Escena",
    "ver": "Ver",
    "salir": "Salir",
    "volver": "Volver a la película",
    "cambiar_area": "Cambiar de área",
    "solo_lectura": "Solo lectura",
}
IDS = {clave: 32100 + i for i, clave in enumerate(TEXTOS)}


def texto(textos, clave, *valores):
    t = (textos or {}).get(clave) or TEXTOS[clave]
    t = t.replace("%s", "{}")
    try:
        return t.format(*valores) if valores else t
    except (IndexError, ValueError):
        return t


# --- valores ---------------------------------------------------------------------------------
_NUMERO = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)\s*(.*)$")


def partir_valor(v):
    """«21,5 °C» -> (21.5, «21,5», «°C»); si no empieza por un número, (None, v, «»)."""
    m = _NUMERO.match(v or "")
    if not m:
        return None, v or "", ""
    texto_num = m.group(1)
    try:
        return float(texto_num.replace(",", ".")), texto_num, m.group(2).strip()
    except ValueError:
        return None, v or "", ""


def color_temperatura(t):
    if t < 17:
        return "FF5AA9FF"
    if t < 19:
        return "FF4DD0C8"
    if t <= 24:
        return "FF7BD88F"
    if t < 27:
        return "FFFFB547"
    return "FFFF6A4D"


def color_bateria(b):
    if b < 20:
        return "FFFF6A4D"
    if b < 40:
        return "FFFFB547"
    return "FF7BD88F"


def _vatios(numero, unidad):
    u = unidad.lower()
    if u == "kw":
        return numero * 1000
    if u == "mw":
        return numero / 1000.0
    return numero


# clase de dispositivo -> (fracción del aro, color) a partir del número y la unidad
ESCALAS = {
    "temperature": lambda n, u: ((n - 10) / 20.0, color_temperatura(n)),
    "humidity": lambda n, u: (n / 100.0, CIAN),
    "moisture": lambda n, u: (n / 100.0, CIAN),
    "battery": lambda n, u: (n / 100.0, color_bateria(n)),
    "power": lambda n, u: (_vatios(n, u) / 1000.0, AMARILLO),
}


def aro(clase, numero, unidad):
    """(«aro_NN.png», color) o None si esa clase no tiene escala."""
    escala = ESCALAS.get(clase)
    if escala is None or numero is None:
        return None
    fraccion, color = escala(numero, unidad)
    fraccion = min(1.0, max(0.0, fraccion))
    return "aro_%02d.png" % int(round(fraccion * PASOS_ARO)), color


# --- baldosas -----------------------------------------------------------------------------------
class Baldosa(object):
    """Una entidad pintada. `props` va tal cual a las propiedades del ListItem."""

    def __init__(self, entidad, linea1, linea2, props):
        self.entidad = entidad
        self.linea1 = linea1
        self.linea2 = linea2
        self.props = props

    def __repr__(self):
        return "Baldosa(%r, %r, %r)" % (self.entidad, self.linea1, self.linea2)


_ENLACES = (" del ", " de la ", " de los ", " de las ", " de ", " en el ", " en la ", " en ", " - ", " · ")


def sin_area(nombre, area):
    """Quita el área del nombre cuando ya se ve por el contexto: «Ventana del salón» en Salón -> «Ventana».

    HA ya quita el área de delante («Salón Lámpara»); aquí se quita también detrás, con los enlaces de _ENLACES.
    Si no queda nada, se deja el nombre como estaba.
    """
    if not nombre or not area:
        return nombre
    bajo, area_b = nombre.lower(), area.lower()
    if bajo.startswith(area_b + " "):
        resto = nombre[len(area) + 1:].strip()
        return resto[:1].upper() + resto[1:] if resto else nombre
    for enlace in _ENLACES:
        if bajo.endswith(enlace + area_b):
            resto = nombre[:len(nombre) - len(enlace) - len(area)].strip()
            return resto or nombre
    return nombre


def tipo_de(e):
    return listado.TIPOS.get((e.get("d"), e.get("c"))) or listado.TIPOS.get((e.get("d"), None)) or "generico"


def baldosa(e, caducado=False, area_nombre=None, area_propia=None):
    """Cómo se pinta una entidad. area_nombre: en «Ahora mismo» la segunda línea es el área, no el estado.
    area_propia: el nombre de su área, que se quita del nombre (ya se ve por el contexto)."""
    tono = e.get("t") or "info"
    tipo = tipo_de(e)
    nombre = sin_area(e.get("n") or e.get("id") or "", area_propia)
    valor = e.get("v") or ""
    props = {"glifo": "glifos/%s.png" % glifos.glifo(tipo, tono), "halo": "", "lavado": "", "alerta": "",
             "nd": "", "aro": "", "color_aro": "", "valor": "", "unidad": ""}

    if e.get("d") in ESCENAS:
        props.update(clase="escena", bloque=BLOQUE["escena"], color_glifo=GLIFO["escena"])
        return Baldosa(e.get("id"), nombre, area_nombre or "", props)

    if tono == "info":  # valores: aro con escala si la clase la tiene; si no, bloque gris con el glifo en cian
        numero, texto_num, unidad = partir_valor(valor)
        anillo = aro(e.get("c"), numero, unidad)
        props.update(clase="valor", valor=texto_num, unidad=unidad)
        if anillo and not caducado:
            props.update(aro=anillo[0], color_aro=anillo[1], color_glifo=anillo[1], bloque="")
        else:
            props.update(bloque=BLOQUE["normal"], color_glifo=SUB if caducado else CIAN)
        return Baldosa(e.get("id"), valor, area_nombre or nombre, props)

    if caducado:  # sin conexión: la forma del glifo sigue diciendo el estado, pero sin color ni halo
        props.update(clase="estado", bloque=BLOQUE["normal"], color_glifo=GLIFO["normal"])
    elif tono == "activo":
        props.update(clase="estado", bloque=BLOQUE["activo"], color_glifo=GLIFO["activo"],
                     halo="halo_activo.png", lavado="lavado_activo.png")
    elif tono == "alerta":
        props.update(clase="estado", bloque=BLOQUE["alerta"], color_glifo=GLIFO["alerta"],
                     halo="halo_alerta.png", lavado="lavado_alerta.png", alerta="1")
    elif tono == "nd":
        props.update(clase="estado", bloque=BLOQUE["nd"], color_glifo=GLIFO["nd"], nd="1")
    else:
        props.update(clase="estado", bloque=BLOQUE["normal"], color_glifo=GLIFO["normal"])
    return Baldosa(e.get("id"), nombre, area_nombre or valor, props)


# --- áreas e indicadores -------------------------------------------------------------------------
class Area(object):
    def __init__(self, ident, nombre, props, baldosas):
        self.id = ident
        self.nombre = nombre
        self.props = props
        self.baldosas = baldosas

    def __repr__(self):
        return "Area(%r, %d)" % (self.id, len(self.baldosas))


def _orden_ahora(e):
    return (0 if e.get("t") == "alerta" else 1,) + listado._orden(e)


def indicadores(entidades, caducado=False):
    """Props de los indicadores de un área: hasta 3 círculos (alertas primero), temperatura o «todo en reposo»."""
    props = {}
    destacadas = [] if caducado else sorted((e for e in entidades if e.get("t") in ("alerta", "activo")),
                                            key=_orden_ahora)
    for i in range(1, MAX_INDICADORES + 1):
        e = destacadas[i - 1] if i <= len(destacadas) else None
        props["ind%d" % i] = "circulo_%s.png" % e["t"] if e else ""
        props["ind%d_glifo" % i] = "glifos/%s.png" % glifos.glifo(tipo_de(e), e["t"]) if e else ""
        props["ind%d_color" % i] = GLIFO[e["t"]] if e else ""
    temperaturas = [e for e in sorted(entidades, key=listado._orden)
                    if e.get("d") == "sensor" and e.get("c") == "temperature" and e.get("t") != "nd"]
    numero = partir_valor(temperaturas[0].get("v"))[0] if temperaturas else None
    props["temp"] = ("%s°" % ("%.1f" % numero).replace(".", ",")) if numero is not None else ""
    props["temp_color"] = (SUB if caducado else color_temperatura(numero)) if numero is not None else ""
    props["tranquilo"] = "1" if not destacadas and numero is None else ""
    # cuántos círculos hay, para colocar la temperatura detrás
    props["n_ind"] = str(min(len(destacadas), MAX_INDICADORES))
    return props


def areas(vista, textos=None):
    """«Ahora mismo» (si hay algo encendido o en alerta) y las áreas con entidades, en el orden de HA."""
    if not vista or vista.get("estado") == R.SIN_DATOS:
        return []
    caducado = vista.get("estado") == R.CADUCADO
    entidades = vista.get("e") or []
    nombres = {a.get("id"): a.get("n") or a.get("id") for a in vista.get("areas") or []}
    grupos = {}
    for e in entidades:
        grupos.setdefault(e.get("a") or SIN_AREA, []).append(e)
    salida = []
    destacadas = sorted((e for e in entidades if e.get("t") in ("alerta", "activo")), key=_orden_ahora)
    if destacadas:
        props = indicadores(destacadas, caducado)
        props.update(glifo="glifos/bell-ring.png", temp="", temp_color="", tranquilo="")
        salida.append(Area(AHORA, texto(textos, "ahora"), props,
                           [baldosa(e, caducado, nombres.get(e.get("a")) or texto(textos, "sin_area"),
                                    nombres.get(e.get("a"))) for e in destacadas]))
    orden = [a for a in vista.get("areas") or [] if a.get("id") in grupos]
    if SIN_AREA in grupos:
        orden.append({"id": SIN_AREA, "n": texto(textos, "sin_area")})
    for a in orden:
        es = sorted(grupos[a["id"]], key=listado._orden)
        props = indicadores(es, caducado)
        props["glifo"] = "glifos/%s.png" % glifos.glifo_area(a.get("i"))
        salida.append(Area(a["id"], a.get("n") or a["id"], props, [baldosa(e, caducado, area_propia=a.get("n")) for e in es]))
    return salida


# --- cabecera -----------------------------------------------------------------------------------
def cabecera(vista, textos=None):
    """Estado del enlace para la cabecera: texto, glifo y color."""
    estado = vista.get("estado") if vista else R.SIN_DATOS
    if estado == R.AL_DIA:
        return {"estado": texto(textos, "al_dia"), "estado_glifo": "glifos/lan-connect.png", "estado_color": CIAN}
    if estado == R.CADUCADO:
        hora = time.strftime("%H:%M", time.localtime(vista.get("ultimo"))) if vista.get("ultimo") else "--:--"
        return {"estado": texto(textos, "caducado", hora), "estado_glifo": "glifos/lan-disconnect.png",
                "estado_color": "FFFF7068"}
    return {"estado": texto(textos, "esperando"), "estado_glifo": "glifos/timer-sand.png", "estado_color": SUB}


def aviso(vista, textos=None):
    """Texto en el centro cuando no hay nada que pintar (o "")."""
    if not vista or vista.get("estado") == R.SIN_DATOS:
        return texto(textos, "esperando")
    if not vista.get("e"):
        return texto(textos, "nada")
    return ""


def cfg(vista):
    return (vista or {}).get("cfg") or {}


# --- panel lateral (B) -------------------------------------------------------------------------
def lateral(vista, textos=None):
    """(título, baldosas de «Ahora mismo», título de la segunda sección, sus baldosas).

    La segunda sección son las entidades del área de este Kodi (cfg.area). Si no tiene área o no hay nada expuesto
    en ella, «Ahora mismo» puede ocupar también ese hueco.
    """
    if not vista or vista.get("estado") == R.SIN_DATOS:
        return texto(textos, "casa"), [], "", []
    caducado = vista.get("estado") == R.CADUCADO
    c = cfg(vista)
    entidades = vista.get("e") or []
    nombres = {a.get("id"): a.get("n") or a.get("id") for a in vista.get("areas") or []}
    aqui_id = c.get("area")
    aqui = sorted((e for e in entidades if aqui_id and e.get("a") == aqui_id), key=listado._orden)
    destacadas = sorted((e for e in entidades if e.get("t") in ("alerta", "activo")), key=_orden_ahora)
    tope = MAX_AHORA_LATERAL if aqui else MAX_AHORA_LATERAL + MAX_AQUI_LATERAL
    ahora = [baldosa(e, caducado, nombres.get(e.get("a")) or texto(textos, "sin_area"), nombres.get(e.get("a")))
             for e in destacadas[:tope]]
    titulo_aqui = (c.get("area_n") or nombres.get(aqui_id) or "") if aqui else ""
    return (texto(textos, "casa"), ahora, titulo_aqui,
            [baldosa(e, caducado, area_propia=titulo_aqui) for e in aqui[:MAX_AQUI_LATERAL]])


# --- atajo del mando ----------------------------------------------------------------------------
TECLAS = {"roja": "red", "verde": "green", "amarilla": "yellow", "azul": "blue"}


def mapa_teclas(tecla, guion):
    """Contenido de userdata/keymaps/ha_link.xml para abrir el panel lateral durante la reproducción, o None."""
    boton = TECLAS.get(tecla)
    if not boton:
        return None
    orden = "RunScript(%s,lateral)" % guion
    return ("<keymap>\n  <FullscreenVideo>\n    <remote>\n      <%s>%s</%s>\n    </remote>\n"
            "  </FullscreenVideo>\n</keymap>\n" % (boton, orden, boton))
