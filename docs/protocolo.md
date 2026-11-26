# Protocolo del canal HA ↔ Kodi (versión 1)

Contrato entre la integración `kodi_link` y el addon `service.ha_link`. Lo implementan
`custom_components/kodi_link/logica.py` y `enlace.py` (HA) y `addon/service.ha_link/resources/lib/ha_link/receptor.py`
(Kodi). **Un cambio incompatible sube `PROTOCOLO` en los dos lados** y se documenta aquí.

## 1. Transporte

- La integración abre un **WebSocket JSON-RPC** con cada Kodi dado de alta con nivel «Ve» o «Actúa»
  (`ws://<host>:<ws_port>/jsonrpc`, con el host y el puerto de la entrada de la integración Kodi de HA; 9090 por
  defecto). Con nivel «Nada» no se conecta.
- **HA → Kodi:** `JSONRPC.NotifyAll` con `sender: "kodi_link"`. El addon lo recibe en `onNotification` como
  `Other.<mensaje>`.
- **Kodi → HA:** el addon lanza `JSONRPC.NotifyAll` con `xbmc.executeJSONRPC`. Llega a todo cliente WebSocket del
  Kodi como `Other.<mensaje>` con `sender: "service.ha_link"`. Sin credenciales: Kodi no guarda ningún token.
- Cada lado filtra por `sender` (el addon recibe también sus propios mensajes, y la integración los avisos de Kodi).
- **Tamaño:** cada petición, con su sobre JSON-RPC, por debajo de **30 000 bytes** (el WebSocket de Kodi cierra la
  conexión por encima de 64 KB). La foto y los cambios grandes se trocean.
- Todos los mensajes llevan `"p": 1` (versión). El addon ignora los de otra versión y lo avisa en el log.

## 2. Mensajes de HA a Kodi

| Mensaje | Campos | Cuándo |
|---|---|---|
| `foto` | `s` sesión, `n` parte (desde 1), `t` total de partes, `nivel` (`ve`/`actua`), `e` entidades; `areas` y `cfg` solo en la parte 1 | Al conectar, cuando el addon la pide y cuando cambian las áreas |
| `cambio` | `s`, `q` secuencia (1, 2, 3…, por sesión), `e` entidades nuevas o cambiadas, `x` ids que dejan de verse | Al cambiar un estado (agrupados en 0,3 s) o una etiqueta, un nombre o un área de una entidad |
| `latido` | `s`, `q` (la última secuencia enviada) | Cada 60 s sin otros mensajes |
| `adios` | — | Reservado: el Kodi deja de recibir datos (borra los suyos) |

Cada foto abre una **sesión nueva** (`s`) y pone la secuencia a 0.

**Área:** `{"id": "salon", "n": "Salón", "i": "sofa"}`, en el orden de la UI de HA (por plantas y, dentro, en el
suyo). Solo las áreas que tienen alguna entidad expuesta. `i` es el icono del área en HA sin el prefijo `mdi:` (no va
si el área no tiene icono o es de otro juego); el addon trae una selección y pinta un plano para los demás.

**Configuración del Kodi (`cfg`, desde 0.2.0):** lo que se elige en HA para ese Kodi y necesita el addon.

| Campo | Qué es |
|---|---|
| `vista` | Lo que se abre desde Programas: `tablero` (A), `filas` (C) o `listado` (K1) |
| `tecla` | Tecla del mando que abre el panel lateral (B) durante la reproducción: `ninguna`, `roja`, `verde`, `amarilla` o `azul` |
| `area`, `area_n` | Id y nombre del área del propio Kodi (la de su `media_player` o su dispositivo); el panel lateral la enseña. No van si no tiene área |

Los campos nuevos son opcionales: un addon 0.1.0 los ignora y un addon 0.2.0 sin `cfg` abre el tablero y no pone
tecla. No sube `PROTOCOLO`.

**Entidad:**

| Campo | Qué es |
|---|---|
| `id` | `entity_id` |
| `n` | Nombre, sin el del área delante («Salón Lámpara» en «Salón» → «Lámpara») |
| `a` | Id del área (de la entidad o de su dispositivo); vacío si no tiene |
| `d` | Dominio |
| `c` | Clase de dispositivo (si tiene) |
| `v` | Valor listo para pintar, en el idioma de HA: estado traducido, número con su precisión, coma decimal y unidad, u hora local en las marcas de tiempo. Vacío en escenas y botones |
| `t` | Tono: `activo` (encendido, abierto, detectado), `normal` (apagado, cerrado), `alerta` (humo, fuga, problema, alarma disparada), `info` (valores y botones) o `nd` (no disponible) |
| `ac` | `1` si ese Kodi podrá accionarla (etiqueta «Kodi: actúa» y nivel «Actúa»). Sin efecto en la fase 1 |

## 3. Mensajes de Kodi a HA

| Mensaje | Campos | Qué hace HA |
|---|---|---|
| `hola` | `v` versión del addon | Al arrancar el servicio. HA manda una foto nueva |
| `ok` | `s` sesión recibida, `v` versión, `n` entidades | Acuse de una foto completa. El enlace pasa a «Conectado» |
| `pedir_foto` | `v` | El addon detecta un hueco (secuencia o sesión que no cuadra). HA manda una foto nueva. Como mucho una petición cada 10 s |

## 4. Reglas del addon

- Una foto se aplica **entera** cuando llegan todas sus partes (en cualquier orden). Una foto de otra sesión a medio
  llegar se descarta.
- Un `cambio` solo se aplica si es de la sesión actual y su `q` es la siguiente. Si no, `pedir_foto`.
- Un `latido` con otra sesión o con otra `q` también provoca `pedir_foto`: así se recupera un cambio perdido aunque
  no lleguen más.
- **Caducidad:** sin noticias de HA durante 150 s, los datos se marcan como antiguos. El listado lo avisa («Sin
  conexión con Home Assistant · Datos de las HH:MM») y pinta los valores en gris.
- La vista se deja en la propiedad `ha_link.vista` de la ventana Home (10000), para el listado y la ventana propia.
  Si el listado está a la vista, el servicio lo refresca (como mucho cada 2 s); la ventana propia se refresca sola.
- Con `cfg.tecla` el servicio escribe `userdata/keymaps/ha_link.xml` (sección `FullscreenVideo`, mando) y recarga
  las teclas; con `ninguna` lo borra. Sin datos de HA no lo toca.

## 4.1 Abrir una ventana desde fuera

`Addons.ExecuteAddon` con `addonid: service.ha_link` y `params: "?abrir=tablero"` (o `filas`, `lateral`) abre esa
ventana; desde HA, con la acción `kodi.call_method`. Sin parámetros abre la que diga `cfg.vista`, y
`?modo=listado` abre siempre el listado.

## 5. Estados del enlace en HA

Sensor de diagnóstico «Enlace» de cada Kodi:

| Estado | Significado |
|---|---|
| `desactivado` | Nivel «Nada»: no se conecta |
| `desconectado` | Kodi apagado o inaccesible. Se reintenta cada 5 s, doblando hasta 60 s, y al momento cuando el `media_player` vuelve a estar disponible |
| `sin_addon` | WebSocket abierto y foto enviada, pero el addon no ha acusado (no instalado, desactivado o de otra versión) |
| `conectado` | El addon ha acusado la última foto |

La conexión se da por muerta si Kodi no contesta a dos latidos seguidos (no se usa el ping de WebSocket).
