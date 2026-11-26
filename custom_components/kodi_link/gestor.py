"""Gestor de kodi_link: qué se expone (por etiqueta), cómo se describe y a qué Kodi se manda."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import floor_registry as fr
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util

from . import logica as L
from .const import (
    AGRUPAR_CAMBIOS, AGRUPAR_REGISTRO, CONF_ETIQUETA_ACTUA, CONF_ETIQUETA_VE, SENAL, SUBENTRY_KODI,
)
from .enlace import Enlace

_LOGGER = logging.getLogger(__name__)
APAGADO = (STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN, None)
EVENTOS_REGISTRO = (er.EVENT_ENTITY_REGISTRY_UPDATED, dr.EVENT_DEVICE_REGISTRY_UPDATED,
                    ar.EVENT_AREA_REGISTRY_UPDATED, fr.EVENT_FLOOR_REGISTRY_UPDATED,
                    lr.EVENT_LABEL_REGISTRY_UPDATED)


class Gestor:
    """Uno por entrada: las etiquetas y los Kodi dados de alta."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.senal = f"{SENAL}_{entry.entry_id}"
        self.etiqueta_ve: str | None = entry.options.get(CONF_ETIQUETA_VE)
        self.etiqueta_actua: str | None = entry.options.get(CONF_ETIQUETA_ACTUA)
        self.enlaces: dict[str, Enlace] = {
            sid: Enlace(self, sub) for sid, sub in entry.subentries.items() if sub.subentry_type == SUBENTRY_KODI}
        self.expuestas: dict[str, dict[str, Any]] = {}
        self.areas: list[dict[str, str]] = []
        self.actuables = 0
        self._actuables: set[str] = set()
        self._registro: dict[str, er.RegistryEntry] = {}
        self._areas_de: dict[str, tuple[str | None, str | None]] = {}
        self._traducciones: dict[str, str] = {}
        self._traducidas: set[str] = set()
        self._pendientes: set[str] = set()
        self._quitar: list = []
        self._quitar_estados = None
        self._cancelar_cambios = None
        self._cancelar_registro = None
        self._cerrojo = asyncio.Lock()

    # --- ciclo de vida -------------------------------------------------------------
    async def arrancar(self) -> None:
        await self._recalcular(enviar=False)
        for evento in EVENTOS_REGISTRO:
            self._quitar.append(self.hass.bus.async_listen(evento, self._registro_cambia))
        kodis = sorted({e.entity_id for e in self.enlaces.values() if e.activo})
        if kodis:
            self._quitar.append(async_track_state_change_event(self.hass, kodis, self._kodi_cambia))
        for enlace in self.enlaces.values():
            enlace.arrancar()

    async def parar(self) -> None:
        while self._quitar:
            self._quitar.pop()()
        for cancelar in (self._quitar_estados, self._cancelar_cambios, self._cancelar_registro):
            if cancelar:
                cancelar()
        self._quitar_estados = self._cancelar_cambios = self._cancelar_registro = None
        await asyncio.gather(*(e.parar() for e in self.enlaces.values()), return_exceptions=True)

    @callback
    def _kodi_cambia(self, event: Event) -> None:
        viejo, nuevo = event.data.get("old_state"), event.data.get("new_state")
        if (viejo.state if viejo else None) in APAGADO and (nuevo.state if nuevo else None) not in APAGADO:
            for enlace in self.enlaces.values():
                if enlace.entity_id == event.data["entity_id"]:
                    enlace.despertar()

    # --- cambios de registro (etiquetas, áreas, nombres) ----------------------------
    @callback
    def _registro_cambia(self, _event: Event) -> None:
        if self._cancelar_registro:
            self._cancelar_registro()
        self._cancelar_registro = async_call_later(self.hass, AGRUPAR_REGISTRO, self._tras_registro)

    @callback
    def _tras_registro(self, _now) -> None:
        self._cancelar_registro = None
        self.entry.async_create_background_task(self.hass, self._recalcular(enviar=True), "kodi_link_registro")

    # --- cambios de estado -----------------------------------------------------------
    @callback
    def _estado_cambia(self, event: Event) -> None:
        self._pendientes.add(event.data["entity_id"])
        if self._cancelar_cambios is None:
            self._cancelar_cambios = async_call_later(self.hass, AGRUPAR_CAMBIOS, self._tras_cambios)

    @callback
    def _tras_cambios(self, _now) -> None:
        self._cancelar_cambios = None
        self.entry.async_create_background_task(self.hass, self._enviar_pendientes(), "kodi_link_cambios")

    async def _enviar_pendientes(self) -> None:
        async with self._cerrojo:
            pendientes, self._pendientes = self._pendientes, set()
            nuevas = dict(self.expuestas)
            for eid in pendientes:
                if eid in self._registro:
                    nuevas[eid] = self._describir(eid)
            await self._aplicar(nuevas, cambian_areas=False)

    # --- cálculo -----------------------------------------------------------------------
    async def _recalcular(self, enviar: bool) -> None:
        async with self._cerrojo:
            ent_reg = er.async_get(self.hass)
            area_reg = ar.async_get(self.hass)
            floor_reg = fr.async_get(self.hass)
            registro: dict[str, er.RegistryEntry] = {}
            actuables: set[str] = set()
            for etiqueta in (self.etiqueta_ve, self.etiqueta_actua):
                if not etiqueta:
                    continue
                for ent in er.async_entries_for_label(ent_reg, etiqueta):
                    if ent.disabled_by is None:
                        registro[ent.entity_id] = ent
                        if etiqueta == self.etiqueta_actua:
                            actuables.add(ent.entity_id)
            self._registro = registro
            self._actuables = actuables
            self.actuables = len(actuables)
            self._areas_de = {}
            for eid in registro:
                self._areas_de[eid] = self.area_de(eid)
            await self._cargar_traducciones(registro.values())
            nuevas = {eid: self._describir(eid) for eid in registro}
            usadas = {a for a, _ in self._areas_de.values() if a}
            areas = L.ordenar_areas(((a.id, a.name, a.floor_id, a.icon) for a in area_reg.async_list_areas()),
                                    [f.floor_id for f in floor_reg.async_list_floors()], usadas)
            cambian_areas = areas != self.areas
            self.areas = areas
            if self._quitar_estados:
                self._quitar_estados()
                self._quitar_estados = None
            if registro:
                self._quitar_estados = async_track_state_change_event(self.hass, sorted(registro), self._estado_cambia)
            if enviar:
                await self._aplicar(nuevas, cambian_areas)
            else:
                self.expuestas = nuevas
            async_dispatcher_send(self.hass, self.senal)

    def area_de(self, eid: str) -> tuple[str | None, str | None]:
        """(id, nombre) del área de una entidad, o la de su dispositivo; (None, None) si no tiene."""
        ent = er.async_get(self.hass).async_get(eid)
        if ent is None:
            return None, None
        area_id = ent.area_id
        if area_id is None and ent.device_id:
            dev = dr.async_get(self.hass).async_get(ent.device_id)
            area_id = dev.area_id if dev else None
        area = ar.async_get(self.hass).async_get_area(area_id) if area_id else None
        return (area.id, area.name) if area else (None, None)

    async def _aplicar(self, nuevas: dict[str, dict], cambian_areas: bool) -> None:
        cambiadas, quitadas = L.diferencias(self.expuestas, nuevas)
        self.expuestas = nuevas
        activos = [e for e in self.enlaces.values() if e.activo]
        if cambian_areas:
            await asyncio.gather(*(e.enviar_foto() for e in activos), return_exceptions=True)
        elif cambiadas or quitadas:
            await asyncio.gather(*(e.enviar_cambios(cambiadas, quitadas) for e in activos), return_exceptions=True)

    async def _cargar_traducciones(self, entradas) -> None:
        idioma = self.hass.config.language
        dominios = {e.domain for e in entradas}
        plataformas = {e.platform for e in entradas if e.translation_key}
        for categoria, integraciones in (("entity_component", dominios), ("entity", plataformas)):
            faltan = {i for i in integraciones if f"{categoria}:{i}" not in self._traducidas}
            if not faltan:
                continue
            try:
                self._traducciones.update(await async_get_translations(self.hass, idioma, categoria, faltan))
            except Exception as err:  # noqa: BLE001 - sin traducción se usa el texto genérico
                _LOGGER.debug("Sin traducciones de %s para %s: %s", categoria, faltan, err)
            self._traducidas |= {f"{categoria}:{i}" for i in faltan}

    def _describir(self, eid: str) -> dict[str, Any]:
        ent = self._registro[eid]
        st = self.hass.states.get(eid)
        area_id, area_nombre = self._areas_de.get(eid, (None, None))
        opciones = ent.options.get("sensor", {}) if ent.options else {}
        precision = opciones.get("display_precision")
        if precision is None:
            precision = opciones.get("suggested_display_precision")
        if st is not None:
            estado, nombre = st.state, st.name
            clase = st.attributes.get("device_class")
            unidad = st.attributes.get("unit_of_measurement")
        else:
            estado, nombre = STATE_UNAVAILABLE, ent.name or ent.original_name or eid
            clase = ent.device_class or ent.original_device_class
            unidad = ent.unit_of_measurement
        return L.describir(entity_id=eid, nombre=nombre, area_id=area_id, area_nombre=area_nombre, estado=estado,
                           clase=clase, unidad=unidad, precision=precision, idioma=self.hass.config.language,
                           traducciones=self._traducciones, zona=dt_util.get_default_time_zone(),
                           ahora=dt_util.now(), plataforma=ent.platform, clave_traduccion=ent.translation_key,
                           actuable=eid in self._actuables)
