"""Avisos de HA en la tele (fase 3): qué tarjeta se pinta para cada aviso. Sin xbmc.

HA manda el mensaje «aviso» con el tipo, la gravedad y lo que este Kodi tiene que hacer con él (`acc`, que se elige
en la subentrada del Kodi): «tarjeta» (sale y se va sola) o «pausar» (se queda hasta cerrarla y pausa el vídeo). El
lenguaje visual es el de K2 (docs/diseno.md §7.1): el icono dice el tipo y el bloque la gravedad.
"""
from . import tablero as T

ACCIONES = ("tarjeta", "pausar")
GRAVEDADES = ("aviso", "importante", "grave")
DURACION = 10  # s si HA no dice otra cosa
DURACION_MAX = 3600  # el mensaje del dashboard puede durar una hora
MAX_TITULO = 80
MAX_MENSAJE = 400

# tipo: glifo de Material Design Icons (los genera herramientas/generar_k2.py)
GLIFOS = {
    "info": "information-variant",
    "timbre": "bell-ring",
    "puerta": "door-open",
    "ventana": "window-open-variant",
    "garaje": "garage-open-variant",
    "movimiento": "motion-sensor",
    "alarma": "shield-lock",
    "humo": "smoke-detector-alert",
    "agua": "water-alert",
    "lluvia": "weather-pouring",
    "calefaccion": "thermostat",
    "luz": "lightbulb-on",
    "sistema": "alert-circle",
}

# gravedad: (bloque, color del glifo, halo, late)
ESTILO = {
    "aviso": (T.BLOQUE["normal"], T.CIAN, "", ""),
    "importante": (T.BLOQUE["activo"], T.GLIFO["activo"], "halo_activo.png", ""),
    "grave": (T.BLOQUE["alerta"], T.GLIFO["alerta"], "halo_alerta.png", "1"),
}


def _texto(valor, tope):
    texto = " ".join(str(valor or "").split())
    return texto if len(texto) <= tope else texto[:tope - 1].rstrip() + "…"


def normalizar(datos):
    """El aviso tal como se pinta, o None si no se puede pintar (sin mensaje ni título, o «nada» que hacer)."""
    if not isinstance(datos, dict):
        return None
    acc = datos.get("acc") if datos.get("acc") in ACCIONES else "tarjeta"
    if datos.get("acc") == "nada":
        return None
    titulo = _texto(datos.get("ti"), MAX_TITULO)
    mensaje = _texto(datos.get("m"), MAX_MENSAJE)
    if not titulo and not mensaje:
        return None
    gravedad = datos.get("g") if datos.get("g") in GRAVEDADES else "aviso"
    tipo = datos.get("tipo") if datos.get("tipo") in GLIFOS else "info"
    try:
        duracion = int(datos.get("d") or DURACION)
    except (TypeError, ValueError):
        duracion = DURACION
    return {"id": str(datos.get("id") or ""), "tipo": tipo, "g": gravedad, "ti": titulo, "m": mensaje,
            "d": max(3, min(duracion, DURACION_MAX)), "acc": acc}


def tarjeta(aviso, textos=None):
    """Propiedades de la ventana del aviso (las imágenes, relativas a media/k2)."""
    bloque, color, halo, late = ESTILO[aviso["g"]]
    titulo = aviso["ti"] or T.texto(textos, "aviso")
    return {"glifo": "glifos/%s.png" % GLIFOS[aviso["tipo"]], "bloque": bloque, "color_glifo": color, "halo": halo,
            "alerta": late, "titulo": titulo, "mensaje": aviso["m"],
            "fija": "1" if aviso["acc"] == "pausar" else "",
            "pista": T.texto(textos, "cerrar_aviso") if aviso["acc"] == "pausar" else ""}


def glifos_avisos():
    """Glifos que necesitan los avisos (para el generador de imágenes y las pruebas)."""
    return sorted(set(GLIFOS.values()))
