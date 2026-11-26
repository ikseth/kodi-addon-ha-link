"""Avisos en la tele (fase 3): una entidad notify por Kodi y otra para todos.

`notify.send_message` (mensaje y título) manda un aviso de gravedad «aviso». La acción `kodi_link.evento` (registrada
en __init__.py sobre estas mismas entidades) añade tipo, gravedad y duración. Lo que cada Kodi hace con cada gravedad
(nada, tarjeta o pausar) se elige en su subentrada.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DURACION_AVISO
from .enlace import Enlace
from .gestor import Gestor

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    gestor: Gestor = entry.runtime_data
    async_add_entities([Avisos(gestor, None)])
    for sid, enlace in gestor.enlaces.items():
        if enlace.activo:
            async_add_entities([Avisos(gestor, enlace)], config_subentry_id=sid)


class Avisos(NotifyEntity):
    """Avisos a un Kodi (enlace) o a todos (enlace None)."""

    _attr_has_entity_name = True
    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(self, gestor: Gestor, enlace: Enlace | None) -> None:
        self.g = gestor
        self.e = enlace
        if enlace is None:
            self._attr_unique_id = f"{gestor.entry.entry_id}_avisos"
            self._attr_translation_key = "avisos_todos"
            self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, gestor.entry.entry_id)})
        else:
            self._attr_unique_id = f"{enlace.id}_avisos"
            self._attr_translation_key = "avisos"
            self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, enlace.id)})

    def _destinos(self) -> list[Enlace]:
        if self.e is not None:
            return [self.e]
        return [e for e in self.g.enlaces.values() if e.activo]

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        await self.async_evento(mensaje=message, titulo=title)

    async def async_evento(self, mensaje: str | None = None, titulo: str | None = None, tipo: str = "info",
                           gravedad: str = "aviso", duracion: int = DURACION_AVISO, **_: Any) -> None:
        enviados = 0
        for enlace in self._destinos():
            if await enlace.enviar_aviso(tipo=tipo, gravedad=gravedad, titulo=titulo, mensaje=mensaje,
                                         duracion=duracion):
                enviados += 1
        _LOGGER.debug("aviso %s/%s a %d Kodi", tipo, gravedad, enviados)
