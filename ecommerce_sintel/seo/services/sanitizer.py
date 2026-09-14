"""
Sanitizacion de html_snippet en SiteMetaTag -- sin dependencias nuevas
(no bleach/nh3), usando html.parser (stdlib) + django.utils.html.format_html
para el auto-escape de valores, mismo criterio que
core/api/serializers.py::_strip_html_fields (defensa en profundidad contra
XSS almacenado, ya certificado en este proyecto).

Politica: html_snippet solo puede contener una o mas etiquetas <meta ...>,
con atributos de una allowlist fija. Cualquier otra etiqueta, atributo
on*=, o valor con 'javascript:'/'data:text/html'/'vbscript:' se rechaza.
"""
from html.parser import HTMLParser

from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.utils.safestring import mark_safe

ALLOWED_ATTRS = {'name', 'content', 'property', 'charset', 'http-equiv'}
FORBIDDEN_VALUE_SUBSTRINGS = ('javascript:', 'data:text/html', 'vbscript:')


class _MetaOnlyParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rebuilt = []
        self.has_disallowed = False
        self.has_text = False

    def handle_starttag(self, tag, attrs):
        self._handle_tag(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self._handle_tag(tag, attrs)

    def handle_endtag(self, tag):
        if tag.lower() != 'meta':
            self.has_disallowed = True

    def handle_data(self, data):
        if data.strip():
            self.has_text = True

    def _handle_tag(self, tag, attrs):
        if tag.lower() != 'meta':
            self.has_disallowed = True
            return

        safe_attrs = []
        for key, value in attrs:
            key_lower = (key or '').strip().lower()
            value = value or ''
            if key_lower.startswith('on'):
                # Atributo de evento (onerror, onload, onclick...): senal
                # inequivoca de intento de XSS -- rechaza todo el snippet en
                # vez de solo descartar el atributo, para no dejar pasar en
                # silencio algo que el admin cree que se guardo.
                self.has_disallowed = True
                continue
            if key_lower not in ALLOWED_ATTRS:
                continue
            if any(bad in value.lower() for bad in FORBIDDEN_VALUE_SUBSTRINGS):
                self.has_disallowed = True
                continue
            safe_attrs.append((key_lower, value))

        if not safe_attrs:
            self.has_disallowed = True
            return

        parts = [format_html('{}="{}"', k, v) for k, v in safe_attrs]
        self.rebuilt.append(str(format_html('<meta {}>', mark_safe(' '.join(str(p) for p in parts)))))


def sanitize_meta_html(raw: str) -> str:
    """
    Valida y reconstruye html_snippet. Devuelve '' si raw esta vacio.
    Lanza ValidationError si contiene algo distinto de <meta> validas.
    """
    raw = (raw or '').strip()
    if not raw:
        return ''

    parser = _MetaOnlyParser()
    try:
        parser.feed(raw)
        parser.close()
    except Exception as exc:
        raise ValidationError(f'HTML invalido: {exc}') from exc

    if parser.has_disallowed or parser.has_text or not parser.rebuilt:
        raise ValidationError(
            'html_snippet solo puede contener una o mas etiquetas <meta> validas '
            '(sin scripts, atributos de evento, ni otro contenido).'
        )

    return '\n'.join(parser.rebuilt)
