"""Servicio de HA Link: la mitad Kodi del canal con Home Assistant.

Solo conecta con Kodi: recibe las notificaciones de la integración kodi_link, deja la vista en una
propiedad de la ventana Home para el listado (plugin.py) y la ventana propia (ventana.py), refresca el listado
si está abierto y mantiene el atajo del mando que abre el panel lateral (userdata/keymaps/ha_link.xml). Lo que se hace con
cada mensaje lo decide resources/lib/ha_link/receptor.py, que no importa Kodi y se prueba con pytest.
"""
import json
import os
import sys
import time

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ID = ADDON.getAddonInfo("id")
VERSION = ADDON.getAddonInfo("version")
sys.path.insert(0, os.path.join(ADDON.getAddonInfo("path"), "resources", "lib"))

from ha_link import receptor  # noqa: E402
from ha_link import tablero  # noqa: E402

EMISOR_HA = "kodi_link"
PROPIEDAD = "ha_link.vista"
VENTANA_HOME = 10000
REFRESCO_MIN = 2.0  # s entre dos refrescos del listado abierto
MAPA = "special://profile/keymaps/ha_link.xml"
GUION = os.path.join(ADDON.getAddonInfo("path"), "ventana.py")


def log(texto, nivel=xbmc.LOGINFO):
    xbmc.log("[%s] %s" % (ID, texto), nivel)


def emitir(mensaje, datos):
    """A HA: le llega como Other.<mensaje> con remitente el id del addon."""
    peticion = {"jsonrpc": "2.0", "id": 1, "method": "JSONRPC.NotifyAll",
                "params": {"sender": ID, "message": mensaje, "data": datos}}
    xbmc.executeJSONRPC(json.dumps(peticion))


class Servicio(xbmc.Monitor):

    def __init__(self):
        super(Servicio, self).__init__()
        self.receptor = receptor.Receptor(VERSION)
        self.ventana = xbmcgui.Window(VENTANA_HOME)
        self.refrescar = False
        self.refrescado = 0.0
        self.avisado_protocolo = False

    def onNotification(self, sender, method, data):
        if sender != EMISOR_HA or not method.startswith("Other."):
            return
        try:
            datos = json.loads(data) if data else {}
        except ValueError:
            log("mensaje ilegible de HA: %s" % method, xbmc.LOGWARNING)
            return
        self.atender(self.receptor.recibir(method[len("Other."):], datos, time.time()))

    def atender(self, salidas):
        for salida in salidas:
            if salida[0] == "publicar":
                self.publicar()
            elif salida[0] == "emitir":
                emitir(salida[1], salida[2])
            elif salida[0] == "protocolo" and not self.avisado_protocolo:
                self.avisado_protocolo = True
                log("HA usa la versión %s del protocolo y este addon la %s: actualizar la que esté atrasada"
                    % (salida[1], receptor.PROTOCOLO), xbmc.LOGWARNING)

    def publicar(self):
        self.ventana.setProperty(PROPIEDAD, json.dumps(self.receptor.vista(time.time()), ensure_ascii=False))
        self.refrescar = True
        self.atajo(self.receptor.cfg.get("tecla"))

    def atajo(self, tecla):
        """Escribe (o borra) el mapa de teclas del panel lateral cuando cambia la tecla elegida en HA."""
        if self.receptor.sesion is None:
            return  # sin datos de HA no se toca lo que haya
        contenido = tablero.mapa_teclas(tecla, GUION)
        ruta = xbmcvfs.translatePath(MAPA)
        actual = None
        if xbmcvfs.exists(ruta):
            with xbmcvfs.File(ruta) as f:
                actual = f.read()
        if contenido == actual:
            return
        if contenido is None:
            xbmcvfs.delete(ruta)
        else:
            xbmcvfs.mkdirs(os.path.dirname(ruta))
            with xbmcvfs.File(ruta, "w") as f:
                f.write(contenido)
        xbmc.executebuiltin("Action(reloadkeymaps)")
        log("tecla del panel lateral: %s" % (tecla or "ninguna"))

    def refrescar_si_abierto(self):
        """El listado se repinta solo si está a la vista, como mucho cada REFRESCO_MIN segundos."""
        if not self.refrescar or time.time() - self.refrescado < REFRESCO_MIN:
            return
        self.refrescar = False
        if xbmc.getInfoLabel("Container.FolderPath").startswith("plugin://%s/" % ID):
            self.refrescado = time.time()
            xbmc.executebuiltin("Container.Refresh")

    def bucle(self):
        log("arranca la versión %s" % VERSION)
        self.publicar()
        self.atender([self.receptor.saludo()])
        while not self.abortRequested():
            if self.waitForAbort(0.5):
                break
            self.atender(self.receptor.revisar(time.time()))
            self.refrescar_si_abierto()
        self.ventana.clearProperty(PROPIEDAD)
        log("termina")


if __name__ == "__main__":
    Servicio().bucle()
