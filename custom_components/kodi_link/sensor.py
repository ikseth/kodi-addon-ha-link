"""Sensores de diagnóstico: cuántas entidades se exponen y el estado del enlace con cada Kodi."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ESTADOS_ENLACE
from .enlace import Enlace
from .gestor import Gestor


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    gestor: Gestor = entry.runtime_data
    async_add_entities([Expuestas(gestor)])
    reg = dr.async_get(hass)
    principal = reg.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    for sid, enlace in gestor.enlaces.items():
        # El dispositivo de cada Kodi se crea aquí y se cuelga del principal con via_device_id: pasar via_device en
        # DeviceInfo está obsoleto (deja de funcionar en HA 2027.8).
        disp = reg.async_get_or_create(config_entry_id=entry.entry_id, config_subentry_id=sid,
                                       identifiers={(DOMAIN, enlace.id)}, name=f"Kodi Link {enlace.nombre}",
                                       manufacturer="kodi-addon-ha-link", model="service.ha_link")
        if principal and disp.via_device_id != principal.id:
            reg.async_update_device(disp.id, via_device_id=principal.id)
        async_add_entities([EstadoEnlace(gestor, enlace)], config_subentry_id=sid)


class _Base(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, gestor: Gestor) -> None:
        self.g = gestor

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(self.hass, self.g.senal, self.async_write_ha_state))


class Expuestas(_Base):
    _attr_translation_key = "expuestas"

    def __init__(self, gestor: Gestor) -> None:
        super().__init__(gestor)
        eid = gestor.entry.entry_id
        self._attr_unique_id = f"{eid}_expuestas"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, eid)}, name="Kodi Link",
                                            manufacturer="kodi-addon-ha-link", model="Kodi Link")

    @property
    def native_value(self) -> int:
        return len(self.g.expuestas)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"actuables": self.g.actuables, "areas": len(self.g.areas)}


class EstadoEnlace(_Base):
    _attr_translation_key = "enlace"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ESTADOS_ENLACE

    def __init__(self, gestor: Gestor, enlace: Enlace) -> None:
        super().__init__(gestor)
        self.e = enlace
        self._attr_unique_id = f"{enlace.id}_enlace"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, enlace.id)})

    @property
    def native_value(self) -> str:
        return self.e.estado

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"kodi": self.e.entity_id, "nivel": self.e.nivel, "version_addon": self.e.version_addon,
                "entidades_enviadas": self.e.entidades_enviadas,
                "ultima_foto": self.e.ultima_foto.isoformat() if self.e.ultima_foto else None}
