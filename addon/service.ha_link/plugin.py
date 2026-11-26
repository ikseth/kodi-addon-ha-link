"""Entrada de HA Link desde Programas: abre la ventana propia (K2) o el listado (K1).

Qué se abre lo decide la configuración de este Kodi en HA (pantalla: tablero, filas o listado). El listado es una
capa fina: lee la vista que deja el servicio en la ventana Home y pinta las filas que calcula
resources/lib/ha_link/listado.py (sin xbmc, con tests). «?modo=listado» lo abre siempre, y
«?abrir=tablero|filas|lateral» abre esa ventana (por ejemplo desde HA con Addons.ExecuteAddon); «&area=<id>» la abre
en esa área. «?abrir=inicio» abre la pantalla elegida en HA (la entrada «Casa» del skin).

«?fila=ahora|aqui|estancias» son las filas de la pantalla de inicio del skin (resources/lib/ha_link/inicio.py): cada
elemento lleva las propiedades de las baldosas de K2 para que el skin lo pinte igual.
"""
import json
import os
import sys
import time
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

ADDON = xbmcaddon.Addon()
RAIZ = ADDON.getAddonInfo("path")
sys.path.insert(0, os.path.join(RAIZ, "resources", "lib"))

from ha_link import inicio  # noqa: E402
from ha_link import listado  # noqa: E402
from ha_link import tablero  # noqa: E402

PROPIEDAD = "ha_link.vista"
ICONOS = os.path.join(RAIZ, "resources", "media", "iconos")
MEDIA = os.path.join(RAIZ, "resources", "skins", "Default", "media", "k2")
GUION = os.path.join(RAIZ, "ventana.py")
IMAGENES = ("glifo", "bloque", "halo", "lavado", "aro", "ind1", "ind1_glifo", "ind2", "ind2_glifo", "ind3",
            "ind3_glifo")
BASE = sys.argv[0]
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].lstrip("-").isdigit() else -1
PARAMS = dict(parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}


def textos():
    return {clave: ADDON.getLocalizedString(ident) for clave, ident in listado.IDS.items()}


def vista():
    try:
        return json.loads(xbmcgui.Window(10000).getProperty(PROPIEDAD) or "null")
    except ValueError:
        return None


def ruta_icono(nombre):
    ruta = os.path.join(ICONOS, nombre)
    if os.path.exists(ruta):
        return ruta
    return os.path.join(ICONOS, "generico_%s" % nombre.rsplit("_", 1)[-1])


def pintar(filas):
    for f in filas:
        li = xbmcgui.ListItem(label=f.etiqueta, label2=f.etiqueta2, offscreen=True)
        if f.icono:
            icono = ruta_icono(f.icono)
            li.setArt({"icon": icono, "thumb": icono})
        url = "%s?%s" % (BASE, urlencode(f.destino)) if f.destino else "%s?nada=1" % BASE
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=f.carpeta)
    xbmcplugin.setContent(HANDLE, "files")
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True, updateListing=False, cacheToDisc=False)


def pintar_fila(nombre, v):
    """Una fila de la pantalla de inicio: baldosas de K2 como elementos de un directorio."""
    t = {clave: ADDON.getLocalizedString(ident) for clave, ident in tablero.IDS.items()}
    for b in inicio.fila(nombre, v, t):
        li = xbmcgui.ListItem(label=b.linea1, label2=b.linea2, offscreen=True)
        li.setProperties({k: (os.path.join(MEDIA, x) if k in IMAGENES and x else x) for k, x in b.props.items()})
        if b.props.get("glifo"):
            li.setArt({"icon": os.path.join(MEDIA, b.props["glifo"])})
        if b.props.get("accion") == "area":
            destino = {"abrir": "tablero", "area": b.entidad}
        else:
            destino = {"ver": b.entidad} if b.entidad else {"nada": "1"}
        xbmcplugin.addDirectoryItem(HANDLE, "%s?%s" % (BASE, urlencode(destino)), li, isFolder=False)
    xbmcplugin.setContent(HANDLE, "files")
    xbmcplugin.endOfDirectory(HANDLE, succeeded=True, updateListing=False, cacheToDisc=False)


def abrir_ventana(que, area=None):
    if HANDLE >= 0:
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
    xbmc.executebuiltin("RunScript(%s,%s%s)" % (GUION, que, ",%s" % area if area else ""))


def main():
    v = vista()
    t = textos()
    if "ver" in PARAMS:  # pulsación en una entidad: en esta fase solo se informa
        info = listado.detalle(v, PARAMS["ver"], t)
        if info:
            xbmcgui.Dialog().notification(info[0], info[1], ruta_icono(info[2]), 3000, False)
        return
    if "nada" in PARAMS:
        return
    if PARAMS.get("fila") in inicio.FILAS:
        pintar_fila(PARAMS["fila"], v)
        return
    pantalla = ((v or {}).get("cfg") or {}).get("vista") or "tablero"
    if PARAMS.get("abrir") == "inicio":
        if pantalla in ("tablero", "filas"):
            abrir_ventana(pantalla)
        else:
            xbmc.executebuiltin("ActivateWindow(Programs,%s?modo=listado,return)" % BASE)
        return
    if PARAMS.get("abrir") in ("tablero", "filas", "lateral"):
        abrir_ventana(PARAMS["abrir"], PARAMS.get("area"))
        return
    if "area" in PARAMS:
        pintar(listado.area(v, PARAMS["area"], time.time(), t))
        return
    if PARAMS.get("modo") != "listado" and pantalla in ("tablero", "filas"):
        abrir_ventana(pantalla)  # la raíz abre la ventana propia y no se queda en un listado vacío
        return
    pintar(listado.raiz(v, time.time(), t))


if __name__ == "__main__":
    try:
        main()
    except Exception as err:  # noqa: BLE001 - que el listado no deje a Kodi esperando
        xbmc.log("[service.ha_link] error en el listado: %s" % err, xbmc.LOGERROR)
        if HANDLE >= 0:
            xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
