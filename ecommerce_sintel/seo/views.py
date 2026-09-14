"""
Vista Django plana (no DRF) que sirve archivos de verificacion en la RAIZ
del dominio (https://sintel.net.co/<filename>.html). Registrada en
ecommerce/urls.py ANTES del catch-all de la SPA -- si no existe un
SiteVerificationFile activo con ese filename, se devuelve 404 (no cae al
catch-all: un .html en la raiz nunca es una ruta valida de la SPA).
"""
from django.http import Http404, HttpResponse


def serve_verification_file(request, filename):
    from seo.services.selectors import VerificationFileSelector

    content = VerificationFileSelector.get_active_content_by_filename(f'{filename}.html')
    if content is None:
        raise Http404()
    return HttpResponse(content, content_type='text/html; charset=utf-8')
