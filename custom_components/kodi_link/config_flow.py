"""Alta y configuración desde la UI: la entrada (etiquetas) y un Kodi por subentrada (nivel, pantalla y tecla)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry, ConfigFlow, ConfigFlowResult, ConfigSubentryFlow, OptionsFlow, SubentryFlowResult,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers import selector as sel

from .const import (
    CONF_ETIQUETA_ACTUA, CONF_ETIQUETA_VE, CONF_KODI, CONF_NIVEL, CONF_TECLA, CONF_VISTA, DOMAIN, NIVEL_VE,
    NIVELES, NOMBRE_ETIQUETA_ACTUA, NOMBRE_ETIQUETA_VE, SUBENTRY_KODI, TECLA_DEFECTO, TECLAS, VISTA_DEFECTO, VISTAS,
)

_ETIQUETA = sel.LabelSelector()
_NIVEL = sel.SelectSelector(sel.SelectSelectorConfig(options=NIVELES, translation_key="nivel",
                                                     mode=sel.SelectSelectorMode.LIST))
_VISTA = sel.SelectSelector(sel.SelectSelectorConfig(options=VISTAS, translation_key="vista",
                                                     mode=sel.SelectSelectorMode.LIST))
_TECLA = sel.SelectSelector(sel.SelectSelectorConfig(options=TECLAS, translation_key="tecla",
                                                     mode=sel.SelectSelectorMode.DROPDOWN))
ICONO_ETIQUETA = "mdi:kodi"


def _campos_kodi(actual: dict[str, Any]) -> dict:
    """Nivel, pantalla y tecla: lo que se puede cambiar de cada Kodi."""
    return {
        vol.Required(CONF_NIVEL, default=actual.get(CONF_NIVEL, NIVEL_VE)): _NIVEL,
        vol.Required(CONF_VISTA, default=actual.get(CONF_VISTA, VISTA_DEFECTO)): _VISTA,
        vol.Required(CONF_TECLA, default=actual.get(CONF_TECLA, TECLA_DEFECTO)): _TECLA,
    }


def _esquema_etiquetas(actual: dict[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Optional(CONF_ETIQUETA_VE, description={"suggested_value": actual.get(CONF_ETIQUETA_VE)}): _ETIQUETA,
        vol.Optional(CONF_ETIQUETA_ACTUA,
                     description={"suggested_value": actual.get(CONF_ETIQUETA_ACTUA)}): _ETIQUETA,
    })


def _etiquetas(hass: HomeAssistant, datos: dict[str, Any]) -> dict[str, str]:
    """Las etiquetas elegidas; las que se dejan en blanco se crean (o se reutilizan) con su nombre por defecto."""
    reg = lr.async_get(hass)
    salida: dict[str, str] = {}
    for clave, nombre, color in ((CONF_ETIQUETA_VE, NOMBRE_ETIQUETA_VE, "light-blue"),
                                 (CONF_ETIQUETA_ACTUA, NOMBRE_ETIQUETA_ACTUA, "amber")):
        elegida = datos.get(clave)
        if elegida:
            salida[clave] = elegida
            continue
        existente = reg.async_get_label_by_name(nombre)
        if existente is None:
            existente = reg.async_create(nombre, icon=ICONO_ETIQUETA, color=color)
        salida[clave] = existente.label_id
    return salida


class KodiLinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Una sola entrada por instalación de HA."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errores: dict[str, str] = {}
        if user_input is not None:
            if user_input.get(CONF_ETIQUETA_VE) and user_input.get(CONF_ETIQUETA_VE) == user_input.get(
                    CONF_ETIQUETA_ACTUA):
                errores["base"] = "etiquetas_iguales"
            else:
                return self.async_create_entry(title="Kodi Link", data={},
                                               options=_etiquetas(self.hass, user_input))
        return self.async_show_form(step_id="user", data_schema=_esquema_etiquetas(user_input or {}),
                                    errors=errores)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return OpcionesFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry: ConfigEntry) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_KODI: KodiFlow}


class OpcionesFlow(OptionsFlow):
    """Cambiar las etiquetas."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errores: dict[str, str] = {}
        if user_input is not None:
            if user_input.get(CONF_ETIQUETA_VE) and user_input.get(CONF_ETIQUETA_VE) == user_input.get(
                    CONF_ETIQUETA_ACTUA):
                errores["base"] = "etiquetas_iguales"
            else:
                return self.async_create_entry(data=_etiquetas(self.hass, user_input))
        actual = user_input if user_input is not None else dict(self.config_entry.options)
        return self.async_show_form(step_id="init", data_schema=_esquema_etiquetas(actual), errors=errores)


class KodiFlow(ConfigSubentryFlow):
    """Dar de alta un Kodi o cambiar su nivel, su pantalla y su tecla."""

    def _titulo(self, entity_id: str) -> str:
        st = self.hass.states.get(entity_id)
        return (st.name if st else None) or entity_id

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        errores: dict[str, str] = {}
        if user_input is not None:
            usados = {s.data.get(CONF_KODI) for s in self._get_entry().subentries.values()}
            if user_input[CONF_KODI] in usados:
                errores[CONF_KODI] = "ya_dado_de_alta"
            else:
                return self.async_create_entry(title=self._titulo(user_input[CONF_KODI]), data=dict(user_input),
                                               unique_id=user_input[CONF_KODI])
        actual = user_input or {}
        esquema = vol.Schema({
            vol.Required(CONF_KODI, default=actual.get(CONF_KODI, vol.UNDEFINED)): sel.EntitySelector(
                sel.EntitySelectorConfig(domain="media_player", integration="kodi")),
            **_campos_kodi(actual),
        })
        return self.async_show_form(step_id="user", data_schema=esquema, errors=errores)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        sub = self._get_reconfigure_subentry()
        if user_input is not None:
            return self.async_update_and_abort(self._get_entry(), sub, data={**sub.data, **user_input})
        esquema = vol.Schema(_campos_kodi(dict(sub.data)))
        return self.async_show_form(step_id="reconfigure", data_schema=esquema)
