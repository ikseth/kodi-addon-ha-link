"""Lógica pura de kodi_link (sin Home Assistant): qué se manda al addon y cómo se trocea.

Contrato con el addon en docs/protocolo.md. Un cambio incompatible sube PROTOCOLO.
"""
from __future__ import annotations

import json
from datetime import datetime, tzinfo
from typing import Any, Callable, Iterable

PROTOCOLO = 1
# El WebSocket de Kodi corta la conexión por encima de 64 KB (fase 0). Cada petición completa,
# con su sobre JSON-RPC, se queda por debajo de este límite.
LIMITE = 30000

# Tonos: el addon elige color e icono con ellos.
ACTIVO = "activo"  # encendido, abierto, detectado
NORMAL = "normal"  # apagado, cerrado, en reposo
ALERTA = "alerta"  # humo, fuga, problema, alarma disparada
INFO = "info"  # valores (temperaturas, potencias) y botones
NO_DISPONIBLE = "nd"

NO_HAY = ("unavailable", "unknown")
ENCENDIBLES = ("light", "switch", "fan", "input_boolean", "automation", "siren", "humidifier")
BOTONES = ("scene", "button", "input_button")
# binary_sensor en los que «on» es un problema, no solo «activo»
BINARIOS_ALERTA = ("smoke", "gas", "moisture", "problem", "safety", "carbon_monoxide", "tamper", "heat",
                   "cold", "battery")
COMA_DECIMAL = ("es", "ca", "gl", "eu", "fr", "de", "it", "pt", "nl", "da", "sv", "nb", "fi", "pl", "cs", "ru",
                "uk", "tr", "ro", "hu", "el", "bg", "hr", "sk", "sl", "lt", "lv", "et")

# Estados que no traen traducción del componente (o cuando no se pudo cargar).
GENERICOS = {
    "es": {"unavailable": "No disponible", "unknown": "Desconocido", "on": "Encendido", "off": "Apagado",
           "open": "Abierto", "closed": "Cerrado", "opening": "Abriendo", "closing": "Cerrando",
           "locked": "Cerrado", "unlocked": "Abierto"},
    "en": {"unavailable": "Unavailable", "unknown": "Unknown", "on": "On", "off": "Off", "open": "Open",
           "closed": "Closed", "opening": "Opening", "closing": "Closing", "locked": "Locked",
           "unlocked": "Unlocked"},
}


def _json(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def tamano(obj: Any) -> int:
    """Bytes que ocupa obj en el canal."""
    return len(_json(obj).encode("utf-8"))


def peticion(mensaje: str, datos: dict[str, Any], emisor: str, ident: int) -> str:
    """Petición JSON-RPC que llega al addon como Other.<mensaje> con remitente emisor."""
    return _json({"jsonrpc": "2.0", "id": ident, "method": "JSONRPC.NotifyAll",
                  "params": {"sender": emisor, "message": mensaje, "data": datos}})


# --- descripción de una entidad -------------------------------------------------------------------
def nombre_corto(nombre: str, area: str | None) -> str:
    """Quita el nombre del área del principio: «Salón Temperatura» en «Salón» queda «Temperatura»."""
    if not area or not nombre:
        return nombre
    if nombre.lower().startswith(area.lower()):
        resto = nombre[len(area):].lstrip(" -:·")
        if resto:
            return resto[0].upper() + resto[1:]
    return nombre


def numero(valor: str, precision: int | None, idioma: str) -> str | None:
    """«21.53» con precisión 1 en español da «21,5». None si no es un número."""
    try:
        x = float(valor)
    except (TypeError, ValueError):
        return None
    if x != x or x in (float("inf"), float("-inf")):
        return None
    if precision is not None:
        texto = f"{x:.{max(0, int(precision))}f}"
    elif x == int(x) and "." not in str(valor) and "e" not in str(valor).lower():
        texto = str(int(x))
    else:
        texto = f"{x:.2f}".rstrip("0").rstrip(".")
    if texto in ("-0", "-0.0", "-0.00"):
        texto = texto[1:]
    if idioma.split("-")[0] in COMA_DECIMAL:
        texto = texto.replace(".", ",")
    return texto


def hora(valor: str, zona: tzinfo, ahora: datetime) -> str | None:
    """Marca de tiempo ISO en hora local: «18:05» si es de hoy, «24/11 18:05» si no."""
    try:
        dt = datetime.fromisoformat(str(valor))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    dt = dt.astimezone(zona)
    hoy = ahora.astimezone(zona).date()
    return dt.strftime("%H:%M") if dt.date() == hoy else dt.strftime("%d/%m %H:%M")


# hvac_action que cuentan como «encendido»: un termostato en modo calor que no está calentando está en reposo
ACCIONES_CLIMA = ("heating", "cooling", "drying", "preheating", "defrosting")


def tono(dominio: str, clase: str | None, estado: str, accion: str | None = None) -> str:
    if estado in NO_HAY:
        return NO_DISPONIBLE
    if dominio == "binary_sensor":
        if estado == "on":
            return ALERTA if clase in BINARIOS_ALERTA else ACTIVO
        return NORMAL
    if dominio in ENCENDIBLES:
        return ACTIVO if estado == "on" else NORMAL
    if dominio == "script":
        return ACTIVO if estado == "on" else INFO
    if dominio == "cover":
        return NORMAL if estado == "closed" else ACTIVO
    if dominio == "lock":
        if estado in ("jammed", "open"):
            return ALERTA
        return NORMAL if estado == "locked" else ACTIVO
    if dominio == "alarm_control_panel":
        if estado == "triggered":
            return ALERTA
        return NORMAL if estado == "disarmed" else ACTIVO
    if dominio == "climate":
        if estado == "off":
            return NORMAL
        if accion is not None:  # si el termostato dice lo que hace, manda eso y no el modo
            return ACTIVO if accion in ACCIONES_CLIMA else NORMAL
        return ACTIVO
    return INFO


def texto_estado(dominio: str, clase: str | None, estado: str, idioma: str,
                 traducciones: dict[str, str], plataforma: str | None = None,
                 clave_traduccion: str | None = None) -> str:
    """Estado traducido como lo enseña HA. Busca de lo más concreto a lo más general."""
    claves = []
    if plataforma and clave_traduccion:
        claves.append(f"component.{plataforma}.entity.{dominio}.{clave_traduccion}.state.{estado}")
    if clase:
        claves.append(f"component.{dominio}.entity_component.{clase}.state.{estado}")
    claves.append(f"component.{dominio}.entity_component._.state.{estado}")
    for clave in claves:
        if traducciones.get(clave):
            return traducciones[clave]
    genericos = GENERICOS.get(idioma.split("-")[0], GENERICOS["en"])
    return genericos.get(estado, estado)


def describir(*, entity_id: str, nombre: str, area_id: str | None, area_nombre: str | None, estado: str,
              clase: str | None = None, unidad: str | None = None, precision: int | None = None,
              idioma: str = "en", traducciones: dict[str, str] | None = None, zona: tzinfo | None = None,
              ahora: datetime | None = None, plataforma: str | None = None,
              clave_traduccion: str | None = None, actuable: bool = False,
              accion: str | None = None) -> dict[str, Any]:
    """Descripción compacta que recibe el addon (ver docs/protocolo.md)."""
    dominio = entity_id.split(".", 1)[0]
    traducciones = traducciones or {}
    t = tono(dominio, clase, estado, accion)
    valor: str | None = None
    if estado in NO_HAY:
        valor = texto_estado(dominio, clase, estado, idioma, traducciones)
    elif dominio == "sensor" and clase == "timestamp" and zona is not None and ahora is not None:
        valor = hora(estado, zona, ahora)
    elif dominio in ("sensor", "number", "input_number"):
        n = numero(estado, precision, idioma)
        if n is not None:
            valor = f"{n} {unidad}" if unidad else n
    elif dominio in BOTONES:
        valor = ""  # su estado es la hora de la última pulsación: no dice nada en la lista
    if valor is None:
        valor = texto_estado(dominio, clase, estado, idioma, traducciones, plataforma, clave_traduccion)
    d: dict[str, Any] = {"id": entity_id, "n": nombre_corto(nombre, area_nombre), "a": area_id or "",
                         "d": dominio, "v": valor, "t": t}
    if clase:
        d["c"] = clase
    if actuable:
        d["ac"] = 1
    return d


def con_nivel(desc: dict[str, Any], puede_actuar: bool) -> dict[str, Any]:
    """Lo que ve un Kodi concreto: sin «ac» si su nivel no le deja actuar."""
    if puede_actuar or "ac" not in desc:
        return desc
    return {k: v for k, v in desc.items() if k != "ac"}


# --- áreas -----------------------------------------------------------------------------------------
def icono_mdi(icono: str | None) -> str | None:
    """«mdi:sofa» -> «sofa». Otros juegos de iconos no se pueden pintar en Kodi: None."""
    if icono and icono.startswith("mdi:") and len(icono) > 4:
        return icono[4:]
    return None


def ordenar_areas(areas: Iterable[tuple], plantas: list[str], usadas: set[str]) -> list[dict[str, str]]:
    """Áreas usadas en el orden de la UI de HA: por planta (en su orden) y, dentro, en el suyo.

    areas: (id, nombre, planta[, icono]) en el orden del registro. plantas: ids en el orden del registro.
    El icono del área («mdi:sofa») va en «i» sin el prefijo, si lo tiene.
    """
    posicion = {p: i for i, p in enumerate(plantas)}
    lista = []
    for i, area in enumerate(areas):
        aid, nombre, planta = area[0], area[1], area[2]
        if aid in usadas:
            orden = posicion.get(planta, len(plantas)) if planta else len(plantas)
            lista.append((orden, i, aid, nombre, icono_mdi(area[3]) if len(area) > 3 else None))
    lista.sort(key=lambda t: (t[0], t[1]))
    salida = []
    for _, _, aid, nombre, icono in lista:
        d = {"id": aid, "n": nombre}
        if icono:
            d["i"] = icono
        salida.append(d)
    return salida


# --- mensajes --------------------------------------------------------------------------------------
def diferencias(antes: dict[str, dict], ahora: dict[str, dict]) -> tuple[list[dict], list[str]]:
    """Entidades nuevas o cambiadas, y las que ya no se exponen."""
    cambiadas = [d for eid, d in ahora.items() if antes.get(eid) != d]
    quitadas = sorted(eid for eid in antes if eid not in ahora)
    return cambiadas, quitadas


def _lotes(elementos: list, base: Callable[[list], dict], limite: int) -> list[list]:
    """Reparte elementos en lotes cuyo mensaje (base(lote)) no pasa de limite bytes."""
    lotes: list[list] = []
    actual: list = []
    for el in elementos:
        prueba = actual + [el]
        if actual and tamano(base(prueba)) > limite:
            lotes.append(actual)
            actual = [el]
        else:
            actual = prueba
        if tamano(base(actual)) > limite:
            raise ValueError(f"Un elemento no cabe en un mensaje: {str(el)[:80]}")
    if actual:
        lotes.append(actual)
    return lotes


def _sobre(datos: dict[str, Any]) -> dict[str, Any]:
    """Lo que ocupa la petición entera, para medir con margen."""
    return {"jsonrpc": "2.0", "id": 999999, "method": "JSONRPC.NotifyAll",
            "params": {"sender": "x" * 20, "message": "cambio", "data": datos}}


def mensajes_foto(sesion: str, areas: list[dict], entidades: list[dict], nivel: str,
                  limite: int = LIMITE, cfg: dict | None = None) -> list[dict[str, Any]]:
    """La foto completa troceada. Las áreas y la configuración del Kodi van en la primera parte; total ≥ 1."""
    def base(lote, primera=False):
        datos = {"p": PROTOCOLO, "s": sesion, "n": 999, "t": 999, "nivel": nivel, "e": lote}
        if primera:
            datos["areas"] = areas
            if cfg:
                datos["cfg"] = cfg
        return _sobre(datos)

    entidades = sorted(entidades, key=lambda d: d["id"])
    if tamano(base([], True)) > limite:
        raise ValueError("Las áreas no caben en un mensaje")
    lotes: list[list] = []
    resto = list(entidades)
    primera: list = []
    while resto and tamano(base(primera + [resto[0]], True)) <= limite:
        primera.append(resto.pop(0))
    lotes.append(primera)
    lotes += _lotes(resto, base, limite)
    total = len(lotes)
    salida = []
    for i, lote in enumerate(lotes, 1):
        datos = {"p": PROTOCOLO, "s": sesion, "n": i, "t": total, "nivel": nivel, "e": lote}
        if i == 1:
            datos["areas"] = areas
            if cfg:
                datos["cfg"] = cfg
        salida.append(datos)
    return salida


def lotes_cambio(cambiadas: list[dict], quitadas: list[str], limite: int = LIMITE) -> list[tuple[list, list]]:
    """Cambios repartidos en lotes que caben en un mensaje cada uno (sin secuencia aún)."""
    elementos = [("e", d) for d in sorted(cambiadas, key=lambda d: d["id"])] + [("x", x) for x in quitadas]

    def base(lote):
        return _sobre({"p": PROTOCOLO, "s": "x" * 12, "q": 99999999,
                       "e": [v for k, v in lote if k == "e"], "x": [v for k, v in lote if k == "x"]})

    return [([v for k, v in lote if k == "e"], [v for k, v in lote if k == "x"])
            for lote in _lotes(elementos, base, limite)]


# --- avisos (fase 3) ----------------------------------------------------------------------------------
MAX_TITULO_AVISO = 80
MAX_MENSAJE_AVISO = 400


def aviso(*, ident: str, tipo: str, gravedad: str, titulo: str | None, mensaje: str | None, duracion: int,
          accion: str) -> dict[str, Any] | None:
    """Mensaje «aviso» para un Kodi, o None si no hay nada que enseñar (sin texto o comportamiento «nada»).

    `accion` es lo que ese Kodi hace con esa gravedad (lo elige su subentrada): «tarjeta» o «pausar».
    """
    titulo = " ".join(str(titulo or "").split())[:MAX_TITULO_AVISO]
    mensaje = " ".join(str(mensaje or "").split())[:MAX_MENSAJE_AVISO]
    if accion not in ("tarjeta", "pausar") or not (titulo or mensaje):
        return None
    return {"p": PROTOCOLO, "id": ident, "tipo": tipo, "g": gravedad, "ti": titulo, "m": mensaje,
            "d": max(3, min(int(duracion), 3600)), "acc": accion}
