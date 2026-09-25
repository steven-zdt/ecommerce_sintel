"""
PLAN_LLMDINAMICO FASE 3 (2026-09-25) -- guard SSRF del ADK (copia stdlib de ai_provider/services/url_guard.py; el ADK no importa Django).

Un administrador puede escribir cualquier URL en /panel/soporte/ia-config y Django la llama desde dentro de la red Docker (probar
conexion, descubrir modelos). Aqui se bloquea lo que nunca es un motor LLM legitimo: metadatos de nube, link-local, la API de Docker,
esquemas no http(s) y URLs con credenciales.

Se PERMITEN a proposito loopback, RFC1918 y nombres de la red Docker (sintel_ollama, host.docker.internal): es como corre Ollama/LM Studio
en este proyecto. Limites conocidos: un nombre que resuelve a una IP publica distinta despues (DNS rebinding) no se detecta aqui, y un
host que no resuelve en el momento de guardar se acepta (se valida otra vez al probar). Los redirects se desactivan en los adapters.
"""
import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_HOSTNAMES = frozenset({'metadata', 'metadata.google.internal', 'metadata.goog', 'instance-data'})
BLOCKED_PORTS = frozenset({2375, 2376})  # API de Docker sin/con TLS
_EXTRA_BLOCKED_IPS = tuple(ipaddress.ip_address(a) for a in ('169.254.169.254', 'fd00:ec2::254', '100.100.100.200', '192.0.0.192'))


class UnsafeProviderURL(ValueError):
    """La URL del proveedor apunta a un destino no permitido."""


def _is_blocked_ip(ip) -> bool:
    if getattr(ip, 'ipv4_mapped', None):
        ip = ip.ipv4_mapped
    return (
        ip in _EXTRA_BLOCKED_IPS or ip.is_link_local or ip.is_unspecified or ip.is_multicast
        or (ip.version == 4 and ip.is_reserved)
    )


def _resolve(hostname: str):
    try:
        return {info[4][0] for info in socket.getaddrinfo(hostname, None)}
    except (socket.gaierror, UnicodeError, OSError):
        return set()


def validate_provider_url(url: str, resolve_dns: bool = True) -> str:
    """Devuelve la URL sin cambios si es aceptable; lanza UnsafeProviderURL con un motivo seguro (sin datos sensibles)."""
    parsed = urlparse((url or '').strip())
    if parsed.scheme not in ('http', 'https'):
        raise UnsafeProviderURL('Solo se permiten URLs http:// o https://.')
    hostname = (parsed.hostname or '').lower().rstrip('.')
    if not hostname:
        raise UnsafeProviderURL('La URL no tiene host.')
    if parsed.username or parsed.password:
        raise UnsafeProviderURL('La URL no puede incluir usuario ni contrasena; use el campo de API key.')
    try:
        port = parsed.port
    except ValueError:
        raise UnsafeProviderURL('Puerto invalido.')
    if port in BLOCKED_PORTS:
        raise UnsafeProviderURL('Puerto no permitido (API de Docker).')
    if hostname in BLOCKED_HOSTNAMES:
        raise UnsafeProviderURL('Host de metadatos de nube no permitido.')
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    addresses = {literal} if literal is not None else set()
    if literal is None and resolve_dns:
        addresses = {ipaddress.ip_address(a.split('%')[0]) for a in _resolve(hostname)}
    if any(_is_blocked_ip(ip) for ip in addresses):
        raise UnsafeProviderURL('El host resuelve a una direccion no permitida (metadatos de nube o link-local).')
    return url
