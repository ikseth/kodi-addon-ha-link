"""Filas de la pantalla de inicio del skin (Estuary Adviser): «Ahora mismo», «Aquí» y «Estancias». Sin xbmc.

El skin las pide como contenido de un plugin (plugin://service.ha_link/?fila=...) y pinta cada elemento con las
mismas propiedades que las baldosas de K2 (glifo, bloque, aro...), así que el lenguaje visual es el mismo (§7.1).
Kodi solo vuelve a pedir una fila cuando cambia su dirección: el servicio deja en la ventana Home una revisión por
fila (`revisiones`) que el skin mete en la dirección, y que solo cambia cuando cambia lo que esa fila enseña.
"""
import hashlib
import json

from . import receptor as R
from . import tablero as T

FILAS = ("ahora", "aqui", "estancias")
MAX_FILA = 24  # elementos por fila: una fila de inicio no es el tablero


def _aviso(vista, textos):
    """Sin datos o caducados: un único elemento que lo dice (el skin no enseña filas vacías)."""
    c = T.cabecera(vista, textos)
    props = {"glifo": c["estado_glifo"], "bloque": T.BLOQUE["normal"], "color_glifo": c["estado_color"],
             "clase": "estado"}
    return T.Baldosa(None, c["estado"], "", props)


def _tranquilo(textos):
    props = {"glifo": "glifos/check-circle-outline.png", "bloque": T.BLOQUE["normal"], "color_glifo": T.CIAN,
             "clase": "estado"}
    return T.Baldosa(None, T.texto(textos, "tranquilo"), "", props)


def _sin_datos(vista):
    return not vista or vista.get("estado") == R.SIN_DATOS


def ahora(vista, textos=None):
    """Lo encendido o en alerta de toda la casa, alertas primero; «Todo en reposo» si no hay nada."""
    if _sin_datos(vista):
        return [_aviso(vista, textos)]
    for a in T.areas(vista, textos):
        if a.id == T.AHORA:
            return a.baldosas[:MAX_FILA]
    return [_tranquilo(textos)]


def aqui(vista, textos=None):
    """Las entidades del área de este Kodi (la que tiene en HA). Vacía si no tiene área o no hay nada en ella."""
    if _sin_datos(vista):
        return []
    area = T.cfg(vista).get("area")
    for a in T.areas(vista, textos):
        if area and a.id == area:
            return a.baldosas[:MAX_FILA]
    return []


def titulo_aqui(vista):
    """Título de la fila «Aquí», o "" si no hay nada que enseñar en ella (el skin la oculta con eso)."""
    c = T.cfg(vista) if vista else {}
    if not c.get("area") or not aqui(vista):
        return ""
    nombres = {a.get("id"): a.get("n") for a in (vista or {}).get("areas") or []}
    return c.get("area_n") or nombres.get(c["area"]) or ""


def estancias(vista, textos=None):
    """Una baldosa por área: el icono del área en un bloque del color de lo peor que tenga dentro (alerta, algo
    encendido o en reposo) y la temperatura debajo. Al pulsarla se abre el tablero en ese área."""
    if _sin_datos(vista):
        return [_aviso(vista, textos)]
    caducado = vista.get("estado") == R.CADUCADO
    salida = []
    for a in T.areas(vista, textos):
        if a.id == T.AHORA:
            continue
        bloques = {b.props.get("bloque") for b in a.baldosas}
        peor = "nd" if caducado else next((t for t in ("alerta", "activo") if T.BLOQUE[t] in bloques), "normal")
        props = {"glifo": a.props["glifo"], "bloque": T.BLOQUE[peor], "color_glifo": T.GLIFO[peor],
                 "clase": "estado", "accion": "area"}
        if peor == "activo":
            props["halo"] = "halo_activo.png"
        elif peor == "alerta":
            props.update(halo="halo_alerta.png", alerta="1")
        salida.append(T.Baldosa(a.id, a.nombre, a.props.get("temp") or "", props))
    return salida


def fila(nombre, vista, textos=None):
    return {"ahora": ahora, "aqui": aqui, "estancias": estancias}[nombre](vista, textos)


def revisiones(vista, textos=None):
    """Huella corta de cada fila. Solo cambia si cambia lo que se ve: la potencia de las placas, que se mueve cada
    pocos segundos, no recarga «Estancias» si no cambia su temperatura ni sus indicadores."""
    salida = {}
    for nombre in FILAS:
        contenido = [(b.entidad, b.linea1, b.linea2, sorted(b.props.items())) for b in fila(nombre, vista, textos)]
        salida[nombre] = hashlib.sha1(json.dumps(contenido, ensure_ascii=False).encode("utf-8")).hexdigest()[:10]
    return salida
