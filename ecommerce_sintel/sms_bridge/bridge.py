"""
sms_bridge/bridge.py

Puente HTTP <-> modem GSM SIM5360 (SIM Movistar Colombia, puerto COM5) para
que el contenedor Django (Linux, via Docker Desktop/WSL2) pueda enviar SMS
sin poder abrir un puerto COM de Windows directamente.

Corre en el HOST Windows, FUERA de Docker. Django le habla por HTTP via
host.docker.internal (ver SMS_BRIDGE_URL en ecommerce/settings/base.py y
notifications/clients/sms.py).

Uso:
    python bridge.py

Variables de entorno opcionales:
    SMS_MODEM_PORT   (default: COM5)
    SMS_MODEM_BAUD   (default: 115200)
    SMS_BRIDGE_HOST  (default: 0.0.0.0 -- debe escuchar en todas las interfaces
                       para que host.docker.internal lo alcance desde el contenedor)
    SMS_BRIDGE_PORT  (default: 8765)
    SMS_BRIDGE_TOKEN (debe coincidir con el mismo valor en .env del backend)

Requiere: pip install pyserial
"""
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import serial

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('sms_bridge')

COM_PORT = os.environ.get('SMS_MODEM_PORT', 'COM5')
BAUD_RATE = int(os.environ.get('SMS_MODEM_BAUD', '115200'))
LISTEN_HOST = os.environ.get('SMS_BRIDGE_HOST', '0.0.0.0')  # nosec B104 -- intencional: debe ser alcanzable desde host.docker.internal (ver docstring del modulo)
LISTEN_PORT = int(os.environ.get('SMS_BRIDGE_PORT', '8765'))
AUTH_TOKEN = os.environ.get('SMS_BRIDGE_TOKEN', '')

# El modem AT solo procesa un comando a la vez -- este lock serializa todas
# las peticiones concurrentes que puedan llegar del contenedor.
_lock = threading.Lock()
_ser = None


def _get_serial():
    global _ser
    if _ser is None or not _ser.is_open:
        _ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=5)
        logger.info('Puerto serie %s abierto a %s baudios.', COM_PORT, BAUD_RATE)
    return _ser


def _read_available(ser, wait=0.5):
    time.sleep(wait)
    return ser.read(ser.in_waiting or 1).decode('ascii', errors='ignore')


def send_sms(to: str, message: str) -> dict:
    with _lock:
        ser = _get_serial()
        ser.reset_input_buffer()

        ser.write(b'AT+CMGF=1\r')
        resp = _read_available(ser)
        if 'OK' not in resp:
            raise RuntimeError(f'Modem no respondio a AT+CMGF=1: {resp!r}')

        # Pide reporte de entrega (bit SRR activo en <fo>=49) -- no es
        # obligatorio para enviar, pero permite loguear +CDS si algo mas
        # adelante quiere leerlo del puerto de diagnostico.
        ser.write(b'AT+CSMP=49,167,0,0\r')
        _read_available(ser, wait=0.3)

        ser.reset_input_buffer()
        ser.write(f'AT+CMGS="{to}"\r'.encode('ascii', errors='ignore'))
        prompt = _read_available(ser, wait=0.8)
        if '>' not in prompt:
            raise RuntimeError(f'Modem no dio el prompt de envio: {prompt!r}')

        ser.write(message.encode('ascii', errors='ignore'))
        ser.write(bytes([26]))  # Ctrl+Z -- termina y transmite

        deadline = time.time() + 15
        buf = ''
        while time.time() < deadline:
            time.sleep(0.5)
            buf += ser.read(ser.in_waiting or 1).decode('ascii', errors='ignore')
            if 'OK' in buf or 'ERROR' in buf:
                break

        if 'ERROR' in buf or 'OK' not in buf:
            raise RuntimeError(f'Envio fallido o sin confirmacion: {buf!r}')

        ref = None
        for line in buf.splitlines():
            line = line.strip()
            if line.startswith('+CMGS:'):
                try:
                    ref = int(line.split(':', 1)[1].strip())
                except ValueError:
                    pass
        return {'ok': True, 'message_ref': ref}


def get_status() -> dict:
    with _lock:
        ser = _get_serial()
        result = {}
        for key, cmd in (('sim', 'AT+CPIN?'), ('signal', 'AT+CSQ'), ('operator', 'AT+COPS?')):
            ser.reset_input_buffer()
            ser.write((cmd + '\r').encode('ascii'))
            result[key] = _read_available(ser).strip()
        return result


class Handler(BaseHTTPRequestHandler):
    def _authorized(self):
        if not AUTH_TOKEN:
            return True
        return self.headers.get('X-Bridge-Token') == AUTH_TOKEN

    def _json(self, status, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/status':
            if not self._authorized():
                return self._json(401, {'ok': False, 'error': 'unauthorized'})
            try:
                return self._json(200, {'ok': True, **get_status()})
            except Exception as exc:
                logger.exception('Error consultando estado del modem')
                return self._json(500, {'ok': False, 'error': str(exc)})
        self._json(404, {'ok': False, 'error': 'not found'})

    def do_POST(self):
        if self.path != '/sms/send':
            return self._json(404, {'ok': False, 'error': 'not found'})
        if not self._authorized():
            return self._json(401, {'ok': False, 'error': 'unauthorized'})
        try:
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length) or b'{}')
            to = str(data.get('to', '')).strip()
            message = str(data.get('message', ''))
            if not to or not message:
                return self._json(400, {'ok': False, 'error': "'to' y 'message' son obligatorios"})
            result = send_sms(to, message)
            self._json(200, result)
        except Exception as exc:
            logger.exception('Error enviando SMS')
            self._json(502, {'ok': False, 'error': str(exc)})

    def log_message(self, fmt, *args):
        logger.info('%s - %s', self.address_string(), fmt % args)


def main():
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    logger.info('SMS bridge escuchando en %s:%s (puerto modem=%s)', LISTEN_HOST, LISTEN_PORT, COM_PORT)
    if not AUTH_TOKEN:
        logger.warning('SMS_BRIDGE_TOKEN no configurado -- el puente acepta peticiones sin autenticacion.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if _ser is not None and _ser.is_open:
            _ser.close()


if __name__ == '__main__':
    main()
