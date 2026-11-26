# CLAUDE.md — kodi-addon-ha-link

Leer antes `docs/diseno.md` (manda), `docs/protocolo.md` (contrato entre las dos mitades) y
`docs/fase0-resultados.md`. Estructura y pruebas en el `README.md`.

## Reglas

1. **Sin datos locales.** Ni IPs, ni nombres de equipos, usuarios o estancias, ni la configuración de una instalación
   concreta, aunque el repositorio sea privado. Lo de cada instalación se documenta con esa instalación.
2. **Instalable y configurable.** La integración se configura desde la UI de HA y el addon desde sus ajustes o desde
   HA. Nada que haya que montar a mano en una instalación.
3. **El control de acceso lo aplica HA:** etiqueta, nivel del Kodi y dominio permitido se validan en la integración
   antes de ejecutar cualquier acción. El addon no guarda credenciales.
4. **Mensajes del canal de menos de 32 KB** y estado por cambios: el WebSocket de Kodi corta la conexión por encima de
   64 KB.
5. Kodi 21 o posterior y Python 3. La lógica va en módulos sin `xbmc`, con tests. Lo que toca Kodi va en capas finas.
6. Probar en un Kodi real que no esté reproduciendo y dejarlo como estaba. Commits solo tras validar.
7. Un cambio incompatible del protocolo sube `PROTOCOLO` en `logica.py` y en `receptor.py` y se documenta en
   `docs/protocolo.md`. Los textos del addon se generan con `herramientas/generar_strings.py`.
8. Las ventanas XML de K2 y sus imágenes se generan (`herramientas/generar_ventanas.py` y `generar_k2.py`): se cambia
   el generador, no el fichero. El lenguaje visual aprobado está en `docs/diseno.md` §7.1. Para verlas sin tocar un Kodi
   de casa, el Kodi de escritorio en una pantalla virtual (Xvfb) con un perfil aparte; ojo, el flatpak no hace caso de
   `KODI_DATA`: el perfil se aparta lanzándolo con otro `HOME`.
