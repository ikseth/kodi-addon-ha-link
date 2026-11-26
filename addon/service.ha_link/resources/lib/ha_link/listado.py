"""Modelo del listado (K1): qué filas se pintan, con qué texto, color e icono. Sin xbmc.

plugin.py convierte cada Fila en un ListItem. Los textos llegan en un diccionario (clave -> texto) que
plugin.py saca de strings.po; si Kodi no los entrega se usan los de TEXTOS.
"""
import time

from . import receptor as R

# Colores de Kodi (AARRGGBB), uno por tono. Los iconos llevan el mismo color.
COLORES = {
    "activo": "FFFFB74D",
    "alerta": "FFEF5350",
    "normal": "FF90A4AE",
    "info": "FF4FC3F7",
    "nd": "FF757575",
}
GRIS = "FF9E9E9E"
TONOS = tuple(COLORES)
SIN_AREA = "_sin_area"
AHORA = "_ahora"

# Textos por defecto (es). Las claves son las de IDS (strings.po).
TEXTOS = {
    "esperando": "Esperando datos de Home Assistant…",
    "esperando_2": "Este Kodi tiene que estar dado de alta en la integración Kodi Link",
    "caducado": "Sin conexión con Home Assistant",
    "caducado_2": "Datos de las {}",
    "nada_expuesto": "No hay nada expuesto para este Kodi",
    "nada_expuesto_2": "Se elige en Home Assistant con las etiquetas de Kodi Link",
    "ahora": "Ahora mismo",
    "sin_area": "Sin área",
    "alerta_1": "1 alerta",
    "alerta_n": "{} alertas",
    "activo_1": "1 activo",
    "activo_n": "{} activos",
    "todo_en_calma": "Todo en calma",
    "elementos_1": "1 elemento",
    "elementos_n": "{} elementos",
    "solo_lectura": "Solo lectura",
}
IDS = {clave: 32000 + i for i, clave in enumerate(TEXTOS)}

# Orden dentro de un área: primero los indicadores, luego valores, mandos y botones.
GRUPO = {
    "alarm_control_panel": 0, "binary_sensor": 1, "lock": 1, "cover": 1,
    "sensor": 2, "number": 2, "input_number": 2, "climate": 2,
    "light": 3, "switch": 3, "fan": 3, "input_boolean": 3, "siren": 3, "humidifier": 3, "media_player": 3,
    "automation": 4,
    "scene": 5, "script": 5, "button": 5, "input_button": 5,
}

# Tipo de icono por dominio y clase de dispositivo (y por dominio solo, con clave None).
TIPOS = {
    ("binary_sensor", "door"): "puerta", ("binary_sensor", "opening"): "puerta",
    ("binary_sensor", "garage_door"): "garaje", ("binary_sensor", "window"): "ventana",
    ("binary_sensor", "motion"): "movimiento", ("binary_sensor", "occupancy"): "movimiento",
    ("binary_sensor", "presence"): "movimiento", ("binary_sensor", "smoke"): "humo",
    ("binary_sensor", "gas"): "humo", ("binary_sensor", "carbon_monoxide"): "humo",
    ("binary_sensor", "moisture"): "agua", ("binary_sensor", "battery"): "bateria",
    ("binary_sensor", "problem"): "problema", ("binary_sensor", "safety"): "problema",
    ("binary_sensor", "tamper"): "problema", ("binary_sensor", "connectivity"): "red",
    ("binary_sensor", None): "binario",
    ("sensor", "temperature"): "temperatura", ("sensor", "humidity"): "humedad",
    ("sensor", "power"): "energia", ("sensor", "energy"): "energia", ("sensor", "current"): "energia",
    ("sensor", "voltage"): "energia", ("sensor", "battery"): "bateria", ("sensor", "illuminance"): "sol",
    ("sensor", "timestamp"): "reloj", ("sensor", "carbon_dioxide"): "aire", ("sensor", "pm25"): "aire",
    ("sensor", "pm10"): "aire", ("sensor", "volatile_organic_compounds"): "aire", ("sensor", None): "sensor",
    ("light", None): "luz", ("switch", "outlet"): "enchufe", ("switch", None): "interruptor",
    ("input_boolean", None): "interruptor", ("fan", None): "ventilador", ("automation", None): "automatismo",
    ("scene", None): "escena", ("script", None): "script", ("button", None): "boton",
    ("input_button", None): "boton", ("cover", "garage"): "garaje", ("cover", None): "persiana",
    ("lock", None): "candado", ("alarm_control_panel", None): "alarma", ("climate", None): "clima",
    ("media_player", None): "tele", ("person", None): "persona", ("device_tracker", None): "persona",
    ("number", None): "sensor", ("input_number", None): "sensor",
}


class Fila(object):
    """Una línea del listado."""

    def __init__(self, etiqueta, etiqueta2="", icono="", carpeta=False, destino=None, entidad=None):
        self.etiqueta = etiqueta
        self.etiqueta2 = etiqueta2
        self.icono = icono  # nombre de fichero en resources/media/iconos
        self.carpeta = carpeta
        self.destino = destino or {}  # parámetros de la URL del plugin
        self.entidad = entidad

    def __repr__(self):
        return "Fila(%r, %r, %r)" % (self.etiqueta, self.etiqueta2, self.icono)


def color(texto, argb):
    return "[COLOR %s]%s[/COLOR]" % (argb, texto) if texto else ""


def icono(dominio, clase, tono):
    tipo = TIPOS.get((dominio, clase)) or TIPOS.get((dominio, None)) or "generico"
    return "%s_%s.png" % (tipo, tono if tono in TONOS else "info")


def _texto(textos, clave, *valores):
    t = (textos or {}).get(clave) or TEXTOS[clave]
    t = t.replace("%s", "{}")
    try:
        return t.format(*valores) if valores else t
    except (IndexError, ValueError):
        return t


def _plural(textos, base, n):
    return _texto(textos, base + "_1") if n == 1 else _texto(textos, base + "_n", n)


def _orden(e):
    return (GRUPO.get(e.get("d"), 6), (e.get("n") or e.get("id") or "").lower())


def _hora(ts):
    return time.strftime("%H:%M", time.localtime(ts)) if ts else "--:--"


def _por_area(vista):
    grupos = {}
    for e in vista.get("e") or []:
        grupos.setdefault(e.get("a") or SIN_AREA, []).append(e)
    return grupos


def _resumen(entidades, textos, caducado):
    """«1 alerta · 2 activos · 21,5 °C», con color en cada parte."""
    alertas = sum(1 for e in entidades if e.get("t") == "alerta")
    activos = sum(1 for e in entidades if e.get("t") == "activo")
    partes = []
    if alertas:
        partes.append(color(_plural(textos, "alerta", alertas), GRIS if caducado else COLORES["alerta"]))
    if activos:
        partes.append(color(_plural(textos, "activo", activos), GRIS if caducado else COLORES["activo"]))
    temperaturas = [e for e in sorted(entidades, key=_orden)
                    if e.get("d") == "sensor" and e.get("c") == "temperature" and e.get("t") != "nd"]
    if temperaturas:
        partes.append(color(temperaturas[0].get("v", ""), GRIS if caducado else "FFFFFFFF"))
    if not partes:
        partes.append(color(_plural(textos, "elementos", len(entidades)), GRIS))
    return "  ·  ".join(partes)


def _peor(entidades):
    tonos = {e.get("t") for e in entidades}
    for t in ("alerta", "activo"):
        if t in tonos:
            return t
    return "normal"


def _aviso(vista, ahora, textos):
    estado = vista.get("estado") if vista else R.SIN_DATOS
    if estado == R.SIN_DATOS:
        return [Fila(_texto(textos, "esperando"), color(_texto(textos, "esperando_2"), GRIS), "espera_nd.png")]
    if estado == R.CADUCADO:
        return [Fila(color(_texto(textos, "caducado"), COLORES["alerta"]),
                     color(_texto(textos, "caducado_2", _hora(vista.get("ultimo"))), GRIS), "sin_conexion_alerta.png")]
    return []


def raiz(vista, ahora, textos=None):
    """Primera pantalla: aviso si hace falta, «Ahora mismo» y una carpeta por área."""
    filas = _aviso(vista, ahora, textos)
    if not vista or vista.get("estado") == R.SIN_DATOS:
        return filas
    caducado = vista.get("estado") == R.CADUCADO
    entidades = vista.get("e") or []
    if not entidades:
        filas.append(Fila(_texto(textos, "nada_expuesto"), color(_texto(textos, "nada_expuesto_2"), GRIS),
                          "generico_nd.png"))
        return filas
    destacadas = [e for e in entidades if e.get("t") in ("alerta", "activo")]
    peor = _peor(destacadas)
    filas.append(Fila(_texto(textos, "ahora"),
                      _resumen(destacadas, textos, caducado) if destacadas else color(
                          _texto(textos, "todo_en_calma"), GRIS),
                      "ahora_%s.png" % ("nd" if caducado else (peor if destacadas else "normal")),
                      carpeta=True, destino={"area": AHORA}))
    grupos = _por_area(vista)
    orden = [a for a in (vista.get("areas") or []) if a.get("id") in grupos]
    if SIN_AREA in grupos:
        orden.append({"id": SIN_AREA, "n": _texto(textos, "sin_area")})
    for a in orden:
        es = grupos[a["id"]]
        filas.append(Fila(a.get("n") or a["id"], _resumen(es, textos, caducado),
                          "area_%s.png" % ("nd" if caducado else _peor(es)), carpeta=True,
                          destino={"area": a["id"]}))
    return filas


def area(vista, area_id, ahora, textos=None):
    """Las entidades de un área (o las destacadas, con area_id == AHORA), en orden estable."""
    filas = _aviso(vista, ahora, textos)
    if not vista or vista.get("estado") == R.SIN_DATOS:
        return filas
    caducado = vista.get("estado") == R.CADUCADO
    nombres = {a.get("id"): a.get("n") for a in vista.get("areas") or []}
    nombres[SIN_AREA] = _texto(textos, "sin_area")
    if area_id == AHORA:
        entidades = [e for e in vista.get("e") or [] if e.get("t") in ("alerta", "activo")]
        entidades.sort(key=lambda e: (0 if e.get("t") == "alerta" else 1,) + _orden(e))
    else:
        entidades = sorted(_por_area(vista).get(area_id, []), key=_orden)
    for e in entidades:
        t = "nd" if caducado else e.get("t", "info")
        nombre = e.get("n") or e.get("id")
        if area_id == AHORA:
            nombre = "%s  %s" % (nombre, color(nombres.get(e.get("a") or SIN_AREA, ""), GRIS))
        filas.append(Fila(nombre, color(e.get("v", ""), COLORES.get(t, GRIS)), icono(e.get("d"), e.get("c"), t),
                          destino={"ver": e.get("id")}, entidad=e))
    return filas


def detalle(vista, entity_id, textos=None):
    """Lo que se enseña al pulsar una entidad en la fase de solo lectura: (título, texto, icono)."""
    for e in (vista or {}).get("e") or []:
        if e.get("id") == entity_id:
            valor = e.get("v") or ""
            texto = "%s · %s" % (valor, _texto(textos, "solo_lectura")) if valor else _texto(textos, "solo_lectura")
            return e.get("n") or entity_id, texto, icono(e.get("d"), e.get("c"), e.get("t", "info"))
    return None
