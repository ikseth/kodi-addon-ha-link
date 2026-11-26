"""kodi_link en un Home Assistant de pruebas, contra un Kodi falso (servidor WebSocket local)."""
from __future__ import annotations

import asyncio
import json

import pytest
from aiohttp import WSMsgType, web
from homeassistant import config_entries, data_entry_flow
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kodi_link import logica as L
from custom_components.kodi_link.const import (
    ADDON_ID, CONF_ETIQUETA_ACTUA, CONF_ETIQUETA_VE, CONF_KODI, CONF_NIVEL, DOMAIN, EMISOR,
)


class KodiFalso:
    """Servidor WebSocket JSON-RPC mínimo: contesta «OK» y guarda lo que le llega."""

    def __init__(self) -> None:
        self.recibidos: list[dict] = []
        self.clientes: list[web.WebSocketResponse] = []
        self.conexiones = 0
        self.puerto = 0
        self._runner: web.AppRunner | None = None

    async def arrancar(self, puerto: int = 0) -> None:
        app = web.Application()
        app.router.add_get("/jsonrpc", self._ws)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        sitio = web.TCPSite(self._runner, "127.0.0.1", puerto)
        await sitio.start()
        self.puerto = sitio._server.sockets[0].getsockname()[1]

    async def parar(self) -> None:
        for ws in list(self.clientes):
            await ws.close()
        if self._runner:
            await self._runner.cleanup()

    async def _ws(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clientes.append(ws)
        self.conexiones += 1
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            m = json.loads(msg.data)
            assert len(msg.data.encode("utf-8")) < 32 * 1024
            self.recibidos.append(m)
            await ws.send_str(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": "OK"}))
        self.clientes.remove(ws)
        return ws

    async def emitir(self, mensaje: str, datos: dict, remitente: str = ADDON_ID) -> None:
        """Lo que mandaría el addon con JSONRPC.NotifyAll."""
        for ws in self.clientes:
            await ws.send_str(json.dumps({"jsonrpc": "2.0", "method": f"Other.{mensaje}",
                                          "params": {"sender": remitente, "data": datos}}))

    def mensajes(self, nombre: str) -> list[dict]:
        return [m["params"]["data"] for m in self.recibidos
                if m.get("method") == "JSONRPC.NotifyAll" and m["params"]["message"] == nombre
                and m["params"]["sender"] == EMISOR]


async def esperar(condicion, segundos: float = 5) -> None:
    for _ in range(int(segundos * 20)):
        if condicion():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("no se cumplió a tiempo")


@pytest.fixture
async def kodi(socket_enabled):
    k = KodiFalso()
    await k.arrancar()
    yield k
    await k.parar()


def _media_player(hass: HomeAssistant, puerto: int) -> str:
    entrada = MockConfigEntry(domain="kodi", data={"host": "127.0.0.1", "port": 8080, "ws_port": puerto,
                                                   "username": None, "password": None, "ssl": False})
    entrada.add_to_hass(hass)
    ent = er.async_get(hass).async_get_or_create("media_player", "kodi", "kodi-uid", config_entry=entrada,
                                                 suggested_object_id="kodi_prueba")
    hass.states.async_set(ent.entity_id, "idle", {"friendly_name": "Kodi de prueba"})
    return ent.entity_id


def _etiquetas(hass: HomeAssistant) -> tuple[str, str]:
    reg = lr.async_get(hass)
    return reg.async_create("Kodi: ve").label_id, reg.async_create("Kodi: actúa").label_id


def _entidad(hass, dominio, uid, etiqueta, estado, atributos, area=None) -> str:
    reg = er.async_get(hass)
    ent = reg.async_get_or_create(dominio, "demo", uid, suggested_object_id=uid)
    reg.async_update_entity(ent.entity_id, labels={etiqueta}, area_id=area)
    hass.states.async_set(ent.entity_id, estado, atributos)
    return ent.entity_id


async def _montar(hass, kodi, nivel="ve"):
    mp = _media_player(hass, kodi.puerto)
    ve, actua = _etiquetas(hass)
    salon = ar.async_get(hass).async_create("Salón", icon="mdi:sofa").id
    er.async_get(hass).async_update_entity(mp, area_id=salon)
    puerta = _entidad(hass, "binary_sensor", "puerta", ve, "off",
                      {"device_class": "door", "friendly_name": "Puerta del salón"}, salon)
    luz = _entidad(hass, "light", "lampara", actua, "on", {"friendly_name": "Salón Lámpara"}, salon)
    entrada = MockConfigEntry(
        domain=DOMAIN, title="Kodi Link", options={CONF_ETIQUETA_VE: ve, CONF_ETIQUETA_ACTUA: actua},
        subentries_data=[ConfigSubentryData(data={CONF_KODI: mp, CONF_NIVEL: nivel}, subentry_type="kodi",
                                            title="Kodi de prueba", unique_id=mp)])
    entrada.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entrada.entry_id)
    await hass.async_block_till_done()
    return entrada, puerta, luz, salon, ve


async def test_foto_al_conectar_y_acuse(hass: HomeAssistant, kodi: KodiFalso) -> None:
    entrada, puerta, luz, salon, _ = await _montar(hass, kodi)
    await esperar(lambda: kodi.mensajes("foto"))
    foto = kodi.mensajes("foto")[0]
    assert foto["p"] == L.PROTOCOLO and foto["n"] == 1 and foto["t"] == 1 and foto["nivel"] == "ve"
    assert foto["areas"] == [{"id": salon, "n": "Salón", "i": "sofa"}]
    # configuración del Kodi: pantalla y tecla por defecto, y su propia área (para el panel lateral)
    assert foto["cfg"] == {"vista": "tablero", "tecla": "azul", "area": salon, "area_n": "Salón"}
    por_id = {e["id"]: e for e in foto["e"]}
    assert por_id[puerta]["v"] == "Closed" and por_id[puerta]["t"] == L.NORMAL  # HA de pruebas en inglés
    assert por_id[luz]["n"] == "Lámpara" and por_id[luz]["t"] == L.ACTIVO
    assert "ac" not in por_id[luz]  # nivel «Ve»: no puede actuar

    estado = "sensor.kodi_link_kodi_de_prueba_link"
    assert hass.states.get(estado).state == "sin_addon"
    await kodi.emitir("ok", {"s": foto["s"], "v": "0.1.0"})
    await esperar(lambda: hass.states.get(estado).state == "conectado")
    assert hass.states.get(estado).attributes["version_addon"] == "0.1.0"
    assert hass.states.get("sensor.kodi_link_exposed_entities").state == "2"
    # El dispositivo del Kodi cuelga del principal (via_device_id, sin el via_device obsoleto).
    dreg = dr.async_get(hass)
    principal = dreg.async_get_device(identifiers={(DOMAIN, entrada.entry_id)})
    del_kodi = dreg.async_get(er.async_get(hass).async_get(estado).device_id)
    assert principal and del_kodi.via_device_id == principal.id
    await hass.config_entries.async_unload(entrada.entry_id)


async def test_cambio_de_estado_y_secuencia(hass: HomeAssistant, kodi: KodiFalso) -> None:
    entrada, puerta, luz, _, _ = await _montar(hass, kodi, nivel="actua")
    await esperar(lambda: kodi.mensajes("foto"))
    foto = kodi.mensajes("foto")[0]
    assert {e["id"]: e for e in foto["e"]}[luz]["ac"] == 1  # nivel «Actúa» y etiqueta «Kodi: actúa»
    hass.states.async_set(puerta, "on", {"device_class": "door", "friendly_name": "Puerta del salón"})
    hass.states.async_set(luz, "off", {"friendly_name": "Salón Lámpara"})
    await esperar(lambda: kodi.mensajes("cambio"))
    await asyncio.sleep(0.5)
    cambios = kodi.mensajes("cambio")
    assert len(cambios) == 1  # los dos cambios seguidos salen juntos
    c = cambios[0]
    assert c["s"] == foto["s"] and c["q"] == 1 and c["x"] == []
    assert {e["id"]: e["t"] for e in c["e"]} == {puerta: L.ACTIVO, luz: L.NORMAL}
    # un cambio solo de atributos que no altera lo que se ve no se manda
    hass.states.async_set(luz, "off", {"friendly_name": "Salón Lámpara", "brillo": 3})
    await asyncio.sleep(0.6)
    assert len(kodi.mensajes("cambio")) == 1
    await hass.config_entries.async_unload(entrada.entry_id)


async def test_quitar_etiqueta_y_pedir_foto(hass: HomeAssistant, kodi: KodiFalso) -> None:
    entrada, puerta, luz, _, _ = await _montar(hass, kodi)
    await esperar(lambda: kodi.mensajes("foto"))
    er.async_get(hass).async_update_entity(puerta, labels=set())
    await esperar(lambda: kodi.mensajes("cambio"), 5)
    assert kodi.mensajes("cambio")[0]["x"] == [puerta]
    assert hass.states.get("sensor.kodi_link_exposed_entities").state == "1"
    # el addon arranca (o pierde el hilo) y pide la foto: nueva sesión
    await kodi.emitir("hola", {"v": "0.1.0", "p": 1})
    await esperar(lambda: len(kodi.mensajes("foto")) == 2)
    f1, f2 = kodi.mensajes("foto")
    assert f1["s"] != f2["s"] and [e["id"] for e in f2["e"]] == [luz]
    # lo que manda otro emisor se ignora
    await kodi.emitir("hola", {}, remitente="otro.addon")
    await asyncio.sleep(0.3)
    assert len(kodi.mensajes("foto")) == 2
    await hass.config_entries.async_unload(entrada.entry_id)


async def test_reconecta_y_reenvia_la_foto(hass: HomeAssistant, kodi: KodiFalso) -> None:
    entrada, *_ = await _montar(hass, kodi)
    await esperar(lambda: kodi.mensajes("foto"))
    puerto = kodi.puerto
    await kodi.parar()  # Kodi se reinicia
    estado = "sensor.kodi_link_kodi_de_prueba_link"
    await esperar(lambda: hass.states.get(estado).state == "desconectado")
    nuevo = KodiFalso()
    await nuevo.arrancar(puerto)
    try:
        hass.states.async_set("media_player.kodi_prueba", "off")
        hass.states.async_set("media_player.kodi_prueba", "idle")  # vuelve: se reintenta sin esperar
        await esperar(lambda: nuevo.mensajes("foto"), 5)
        assert hass.states.get(estado).state == "sin_addon"
    finally:
        await hass.config_entries.async_unload(entrada.entry_id)
        await nuevo.parar()


async def test_nivel_nada_no_conecta(hass: HomeAssistant, kodi: KodiFalso) -> None:
    entrada, *_ = await _montar(hass, kodi, nivel="nada")
    await asyncio.sleep(0.5)
    assert kodi.conexiones == 0
    assert hass.states.get("sensor.kodi_link_kodi_de_prueba_link").state == "desactivado"
    await hass.config_entries.async_unload(entrada.entry_id)


async def test_alta_crea_las_etiquetas_y_el_kodi(hass: HomeAssistant, kodi: KodiFalso) -> None:
    mp = _media_player(hass, kodi.puerto)
    res = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert res["type"] is data_entry_flow.FlowResultType.FORM
    res = await hass.config_entries.flow.async_configure(res["flow_id"], {})
    assert res["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    reg = lr.async_get(hass)
    ve, actua = reg.async_get_label_by_name("Kodi: ve"), reg.async_get_label_by_name("Kodi: actúa")
    assert ve and actua
    entrada = hass.config_entries.async_entries(DOMAIN)[0]
    assert entrada.options == {CONF_ETIQUETA_VE: ve.label_id, CONF_ETIQUETA_ACTUA: actua.label_id}
    await hass.async_block_till_done()

    res = await hass.config_entries.subentries.async_init((entrada.entry_id, "kodi"),
                                                          context={"source": config_entries.SOURCE_USER})
    res = await hass.config_entries.subentries.async_configure(
        res["flow_id"], {CONF_KODI: mp, CONF_NIVEL: "ve", "vista": "filas", "tecla": "roja"})
    assert res["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    await esperar(lambda: kodi.mensajes("foto"))
    assert kodi.mensajes("foto")[-1]["cfg"] == {"vista": "filas", "tecla": "roja"}  # sin área: no la lleva
    # el mismo Kodi no se da de alta dos veces
    res = await hass.config_entries.subentries.async_init((entrada.entry_id, "kodi"),
                                                          context={"source": config_entries.SOURCE_USER})
    res = await hass.config_entries.subentries.async_configure(res["flow_id"], {CONF_KODI: mp, CONF_NIVEL: "ve"})
    assert res["errors"] == {CONF_KODI: "ya_dado_de_alta"}
    # reconfigurar: nivel, pantalla y tecla
    sid = next(iter(entrada.subentries))
    res = await hass.config_entries.subentries.async_init(
        (entrada.entry_id, "kodi"), context={"source": config_entries.SOURCE_RECONFIGURE, "subentry_id": sid})
    assert {str(k) for k in res["data_schema"].schema} == {CONF_NIVEL, "vista", "tecla", "con_aviso",
                                                          "con_importante", "con_grave"}
    res = await hass.config_entries.subentries.async_configure(
        res["flow_id"], {CONF_NIVEL: "ve", "vista": "listado", "tecla": "ninguna"})
    assert res["reason"] == "reconfigure_successful"
    assert entrada.subentries[sid].data["vista"] == "listado"
    await hass.async_block_till_done()
    await hass.config_entries.async_unload(entrada.entry_id)


async def test_etiquetas_iguales_es_error(hass: HomeAssistant) -> None:
    ve, _ = _etiquetas(hass)
    res = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    res = await hass.config_entries.flow.async_configure(res["flow_id"],
                                                         {CONF_ETIQUETA_VE: ve, CONF_ETIQUETA_ACTUA: ve})
    assert res["errors"] == {"base": "etiquetas_iguales"}


async def test_avisos_por_notify_y_por_la_accion(hass: HomeAssistant, kodi: KodiFalso) -> None:
    entrada, *_ = await _montar(hass, kodi)
    await esperar(lambda: kodi.mensajes("foto"))
    reg = er.async_get(hass)
    sid = next(iter(entrada.subentries))
    uno = reg.async_get_entity_id("notify", DOMAIN, f"{sid}_avisos")
    todos = reg.async_get_entity_id("notify", DOMAIN, f"{entrada.entry_id}_avisos")
    assert uno and todos
    # notify.send_message: gravedad «aviso», que por defecto es una tarjeta
    await hass.services.async_call("notify", "send_message", {"entity_id": uno, "message": "Hola", "title": "Prueba"},
                                   blocking=True)
    await esperar(lambda: kodi.mensajes("aviso"))
    a = kodi.mensajes("aviso")[-1]
    assert (a["ti"], a["m"], a["g"], a["tipo"], a["acc"], a["p"]) == ("Prueba", "Hola", "aviso", "info", "tarjeta",
                                                                      L.PROTOCOLO)
    # la acción propia, a todos los Kodi: grave pausa por defecto
    await hass.services.async_call(DOMAIN, "evento", {"entity_id": todos, "mensaje": "Humo en la cocina",
                                                      "tipo": "humo", "gravedad": "grave", "duracion": 30},
                                   blocking=True)
    await esperar(lambda: len(kodi.mensajes("aviso")) == 2)
    a = kodi.mensajes("aviso")[-1]
    assert (a["tipo"], a["g"], a["acc"], a["d"]) == ("humo", "grave", "pausar", 30)
    await hass.config_entries.async_unload(entrada.entry_id)
