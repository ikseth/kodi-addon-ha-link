"""Conexión WebSocket con un Kodi: foto al conectar, cambios, latido, acuse del addon y reconexión."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from . import logica as L
from .const import (
    ADDON_ID, CONECTADO, CONF_KODI, CONF_NIVEL, CONF_TECLA, CONF_VISTA, DESACTIVADO, DESCONECTADO, EMISOR,
    ESPERA_MAX, ESPERA_MIN, LATIDO, NIVEL_ACTUA, NIVEL_VE, SIN_ADDON, TECLA_DEFECTO, VISTA_DEFECTO,
)

if TYPE_CHECKING:
    from .gestor import Gestor

_LOGGER = logging.getLogger(__name__)
PUERTO_WS = 9090
CONEXION = 10  # s para abrir el WebSocket


class Enlace:
    """Un Kodi dado de alta (una subentrada) con nivel Ve o Actúa."""

    def __init__(self, gestor: Gestor, sub: ConfigSubentry) -> None:
        self.g = gestor
        self.hass = gestor.hass
        self.id = sub.subentry_id
        self.nombre = sub.title
        self.entity_id: str = sub.data[CONF_KODI]
        self.nivel: str = sub.data.get(CONF_NIVEL, NIVEL_VE)
        self.vista: str = sub.data.get(CONF_VISTA, VISTA_DEFECTO)
        self.tecla: str = sub.data.get(CONF_TECLA, TECLA_DEFECTO)
        self.estado = DESCONECTADO if self.activo else DESACTIVADO
        self.version_addon: str | None = None
        self.ultima_foto = None
        self.entidades_enviadas = 0
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._tarea: asyncio.Task | None = None
        self._despertar = asyncio.Event()
        self._cerrojo = asyncio.Lock()
        self._sesion = ""
        self._sec = 0
        self._id = 0

    @property
    def activo(self) -> bool:
        """Con nivel «Nada» no se conecta: ese Kodi no recibe nada."""
        return self.nivel in (NIVEL_VE, NIVEL_ACTUA)

    @property
    def puede_actuar(self) -> bool:
        return self.nivel == NIVEL_ACTUA

    # --- ciclo de vida -------------------------------------------------------------
    @callback
    def arrancar(self) -> None:
        if not self.activo:
            return
        self._tarea = self.g.entry.async_create_background_task(
            self.hass, self._bucle(), f"kodi_link_{self.entity_id}")

    async def parar(self) -> None:
        if self._tarea:
            self._tarea.cancel()
            try:
                await self._tarea
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._tarea = None
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()

    @callback
    def despertar(self) -> None:
        """El Kodi vuelve a estar disponible: reintentar ya, sin esperar al siguiente intento."""
        self._despertar.set()

    def _url(self) -> str | None:
        ent = er.async_get(self.hass).async_get(self.entity_id)
        entrada = self.hass.config_entries.async_get_entry(ent.config_entry_id) if ent else None
        if entrada is None:
            return None
        host = entrada.data.get("host")
        puerto = entrada.data.get("ws_port") or PUERTO_WS
        return f"ws://{host}:{puerto}/jsonrpc" if host else None

    def _cambia_estado(self, estado: str) -> None:
        if estado != self.estado:
            _LOGGER.info("%s: %s", self.nombre, estado)
            self.estado = estado
        async_dispatcher_send(self.hass, self.g.senal)

    async def _bucle(self) -> None:
        espera = ESPERA_MIN
        avisado = False
        while True:
            url = self._url()
            if url is None:
                if not avisado:
                    _LOGGER.warning("%s: no encuentro la entrada de la integración Kodi de %s",
                                    self.nombre, self.entity_id)
                    avisado = True
            else:
                try:
                    await self._conectar(url)
                    espera = ESPERA_MIN
                except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
                    _LOGGER.debug("%s: sin conexión (%s)", self.nombre, err)
                except Exception:  # noqa: BLE001 - el bucle no debe morir
                    _LOGGER.exception("%s: error en el enlace", self.nombre)
                finally:
                    self._ws = None
                    self._cambia_estado(DESCONECTADO)
            try:
                await asyncio.wait_for(self._despertar.wait(), espera)
                espera = ESPERA_MIN
            except asyncio.TimeoutError:
                espera = min(espera * 2, ESPERA_MAX)
            self._despertar.clear()

    async def _conectar(self, url: str) -> None:
        """Una conexión, hasta que se cierra o deja de responder.

        No se usa el ping de WebSocket: la conexión se da por muerta si Kodi no contesta a dos latidos
        seguidos (cada petición nuestra recibe su respuesta «OK»).
        """
        sesion = async_get_clientsession(self.hass)
        async with asyncio.timeout(CONEXION):
            ws = await sesion.ws_connect(url)
        try:
            self._ws = ws
            self.version_addon = None
            self._cambia_estado(SIN_ADDON)
            await self.enviar_foto()
            latido = LATIDO.total_seconds()
            recibido = self.hass.loop.time()
            while True:
                try:
                    msg = await ws.receive(timeout=latido)
                except asyncio.TimeoutError:
                    if self.hass.loop.time() - recibido > 2 * latido + CONEXION:
                        _LOGGER.debug("%s: no contesta a los latidos, se reconecta", self.nombre)
                        return
                    await self._enviar("latido", {"p": L.PROTOCOLO, "s": self._sesion, "q": self._sec})
                    continue
                if msg.type == aiohttp.WSMsgType.TEXT:
                    recibido = self.hass.loop.time()
                    await self._recibir(msg.data)
                elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSED,
                                  aiohttp.WSMsgType.ERROR):
                    return
        finally:
            self._ws = None
            if not ws.closed:
                await ws.close()

    async def _recibir(self, texto: str) -> None:
        try:
            m = json.loads(texto)
        except ValueError:
            return
        metodo = m.get("method") or ""
        params = m.get("params") or {}
        if not metodo.startswith("Other.") or params.get("sender") != ADDON_ID:
            return  # respuestas a nuestras peticiones y avisos del propio Kodi
        mensaje = metodo[len("Other."):]
        datos = params.get("data") or {}
        if not isinstance(datos, dict):
            datos = {}
        if mensaje in ("hola", "pedir_foto"):
            _LOGGER.debug("%s: el addon pide la foto (%s)", self.nombre, mensaje)
            await self.enviar_foto()
        elif mensaje == "ok" and datos.get("s") == self._sesion:
            self.version_addon = str(datos.get("v") or "") or None
            self._cambia_estado(CONECTADO)

    # --- envíos --------------------------------------------------------------------
    async def _enviar(self, mensaje: str, datos: dict[str, Any]) -> None:
        ws = self._ws
        if ws is None or ws.closed:
            return
        self._id += 1
        await ws.send_str(L.peticion(mensaje, datos, EMISOR, self._id))

    def _cfg(self) -> dict[str, Any]:
        """Configuración de este Kodi que necesita el addon: pantalla, tecla del panel y su propia área."""
        area_id, area_nombre = self.g.area_de(self.entity_id)
        cfg: dict[str, Any] = {"vista": self.vista, "tecla": self.tecla}
        if area_id:
            cfg["area"] = area_id
            cfg["area_n"] = area_nombre
        return cfg

    def _vista(self) -> list[dict]:
        return [L.con_nivel(d, self.puede_actuar) for d in self.g.expuestas.values()]

    async def enviar_foto(self) -> None:
        async with self._cerrojo:
            if self._ws is None:
                return
            self._sesion = uuid.uuid4().hex[:12]
            self._sec = 0
            vista = self._vista()
            partes = L.mensajes_foto(self._sesion, self.g.areas, vista, self.nivel, cfg=self._cfg())
            for datos in partes:
                await self._enviar("foto", datos)
            self.ultima_foto = dt_util.utcnow()
            self.entidades_enviadas = len(vista)
            _LOGGER.debug("%s: foto %s con %d entidades en %d partes", self.nombre, self._sesion, len(vista),
                          len(partes))
        async_dispatcher_send(self.hass, self.g.senal)

    async def enviar_cambios(self, cambiadas: list[dict], quitadas: list[str]) -> None:
        async with self._cerrojo:
            if self._ws is None or not self._sesion:
                return
            cambiadas = [L.con_nivel(d, self.puede_actuar) for d in cambiadas]
            for e, x in L.lotes_cambio(cambiadas, quitadas):
                self._sec += 1
                await self._enviar("cambio", {"p": L.PROTOCOLO, "s": self._sesion, "q": self._sec, "e": e, "x": x})
            self.entidades_enviadas = len(self.g.expuestas)
