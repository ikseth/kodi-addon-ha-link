# Fase 0: prueba del canal HA ↔ Kodi (26/11/2026)

**Resultado: el canal funciona en los dos sentidos.** Se puede seguir con la fase 1.

## Qué se probó

- **Addon de prueba** `fase0/service.ha_link.prueba`: un servicio que, al recibir `Other.ping` con sender `ha_link`,
  contesta con `JSONRPC.NotifyAll` (`pong`) desde el propio Kodi.
- **Cliente** `fase0/probar_canal.py`, que hace de integración de HA:
  - Se conecta al WebSocket JSON-RPC del Kodi (puerto 9090).
  - Manda pings de varios tamaños con `JSONRPC.NotifyAll` y espera el `pong`.
  - Hace lo mismo con la acción `kodi.call_method` de Home Assistant.
- **Equipo:** un Kodi 21.2 sobre LibreELEC 12.2, sin reproducir. Se instaló copiando la carpeta del addon, con
  `UpdateLocalAddons` y `Addons.SetAddonEnabled`. Después se desactivó y se borró.
- **Red:** cliente remoto por VPN, con unos 50 ms de ping en cada sentido. En la red local los tiempos serán menores.

## Resultados

| Camino | Tamaño | Entregados | Ida y vuelta (mediana / máx.) |
|---|---|---|---|
| WebSocket directo | 10 B | 5/5 | 88 / 136 ms |
| WebSocket directo | 1 KB | 5/5 | 88 / 93 ms |
| WebSocket directo | 10 KB | 5/5 | 165 / 221 ms |
| WebSocket directo | 60 KB | 5/5 | 347 / 526 ms |
| WebSocket directo | 250 KB | **corta la conexión** | — |
| `kodi.call_method` de HA | 10 B – 10 KB | 15/15 | 141–207 ms (incluye la llamada REST) |

## Hallazgos que cambian el diseño

1. **Kodi → integración funciona sin credenciales.** Un `JSONRPC.NotifyAll` lanzado desde el addon con
   `xbmc.executeJSONRPC` llega como `Other.<mensaje>` a todo cliente conectado al WebSocket del Kodi, con
   `sender` igual al id del addon. Es el canal de vuelta para las pulsaciones.
2. **Límite de 64 KB por mensaje en el WebSocket de Kodi.** Un mensaje mayor provoca «client buffer size 65536
   exceeded» y Kodi **cierra la conexión**, incluidas las otras peticiones en curso. Consecuencias:
   - El estado se manda **por cambios** (una entidad por mensaje o en pequeños lotes), nunca entero.
   - La foto inicial se trocea por debajo de unos 32 KB por mensaje, con margen.
   - Las imágenes (cámara) no van por el canal: el addon las pide por HTTP a una URL firmada de HA.
3. **El addon recibe también sus propias notificaciones** y las de otros emisores: hay que filtrar por `sender`.
4. **Todos los Kodi de la instalación de referencia son Kodi 21** (Omega, Python 3). No hace falta la variante Leia,
   y el addon puede usar lo que ofrece Kodi 21 para la parte visual.

## Pendiente para la fase 1

- Medir los tiempos desde el propio HA, en la red local.
- Reconexión: qué pasa con los mensajes si el Kodi reinicia o se corta la red. La integración tiene que reenviar la
  foto al reconectar.
