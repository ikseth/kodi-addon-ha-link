"""Fase 0: prueba del canal HA <-> Kodi.

HA -> Kodi: JSONRPC.NotifyAll con sender 'ha_link' llega aquí como onNotification('ha_link', 'Other.<msg>', data).
Kodi -> HA: el addon emite JSONRPC.NotifyAll con sender = su id; lo recibe todo cliente WebSocket/TCP del Kodi.
"""
import json
import time

import xbmc

ID = 'service.ha_link.prueba'
EMISOR_HA = 'ha_link'


def log(msg):
    xbmc.log('[%s] %s' % (ID, msg), xbmc.LOGINFO)


def emitir(mensaje, datos):
    peticion = {'jsonrpc': '2.0', 'id': 1, 'method': 'JSONRPC.NotifyAll',
                'params': {'sender': ID, 'message': mensaje, 'data': datos}}
    return xbmc.executeJSONRPC(json.dumps(peticion))


class Monitor(xbmc.Monitor):
    def onNotification(self, sender, method, data):
        if sender != EMISOR_HA:
            return
        recibido = time.time()
        try:
            datos = json.loads(data) if data else {}
        except ValueError:
            datos = {}
        log('recibido %s (%d bytes)' % (method, len(data or '')))
        if method == 'Other.ping':
            emitir('pong', {'seq': datos.get('seq'), 't_envio': datos.get('t'), 't_kodi': recibido,
                            'bytes': len(data or ''), 'origen': datos.get('origen')})


if __name__ == '__main__':
    monitor = Monitor()
    version = xbmc.getInfoLabel('System.BuildVersion')
    log('arranca en Kodi %s' % version)
    emitir('hola', {'version': version, 't': time.time()})
    while not monitor.abortRequested():
        if monitor.waitForAbort(30):
            break
    log('termina')
