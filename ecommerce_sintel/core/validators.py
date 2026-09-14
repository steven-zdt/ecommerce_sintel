"""
Validadores compartidos del Home Builder.

validate_url_type_pair() centraliza la regla INTERNA/EXTERNA/ANCHOR usada por
FeatureBannerBlock y HomeCard -- un solo lugar en vez de reimplementar la misma
validacion de formato de URL en cada modelo nuevo que agregue botones con url_type.
"""

URL_TYPE_INTERNA = 'INTERNA'
URL_TYPE_EXTERNA = 'EXTERNA'
URL_TYPE_ANCHOR = 'ANCHOR'


def validate_url_type_pair(url_type, url):
    """
    Retorna un mensaje de error (str) si `url` no es coherente con `url_type`,
    o None si es valida. Una URL vacia siempre es valida (boton/link opcional).
    """
    if not url:
        return None
    if url_type == URL_TYPE_INTERNA and not url.startswith('/'):
        return 'Una URL interna debe empezar con "/".'
    if url_type == URL_TYPE_EXTERNA and not (url.startswith('http://') or url.startswith('https://')):
        return 'Una URL externa debe empezar con "http://" o "https://".'
    if url_type == URL_TYPE_ANCHOR and not url.startswith('#'):
        return 'Una ancla debe empezar con "#".'
    return None
