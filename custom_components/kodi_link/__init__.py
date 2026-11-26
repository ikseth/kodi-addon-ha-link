"""Kodi Link: canal entre Home Assistant y Kodi (la mitad HA del addon service.ha_link)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .gestor import Gestor

PLATFORMS = [Platform.SENSOR]

type KodiLinkEntry = ConfigEntry[Gestor]


async def async_setup_entry(hass: HomeAssistant, entry: KodiLinkEntry) -> bool:
    gestor = Gestor(hass, entry)
    entry.runtime_data = gestor
    # El dispositivo principal antes que las entidades: el de cada Kodi cuelga de él (via_device).
    dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.entry_id)},
                                           name="Kodi Link", manufacturer="kodi-addon-ha-link", model="Kodi Link")
    await gestor.arrancar()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_recargar))
    return True


async def _recargar(hass: HomeAssistant, entry: KodiLinkEntry) -> None:
    """Cambiar las etiquetas o dar de alta, cambiar o quitar un Kodi recarga la entrada."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: KodiLinkEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await entry.runtime_data.parar()
    return ok
