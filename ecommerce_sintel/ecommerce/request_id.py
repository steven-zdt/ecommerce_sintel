"""
HARDENING F9 (2026-09-24) -- correlacion: RequestIDMiddleware para HTTP y helper para WebSocket.

El id llega de nginx (`X-Request-ID`, generado con $request_id si el cliente no lo manda). Solo se acepta con forma segura
(8-64 caracteres alfanumericos . _ -); si no, se genera uno nuevo. Se guarda en un ContextVar (lo leen ai_bridge y el filtro de
logs) y se devuelve en la cabecera de respuesta. Aditivo: rollback = quitar de MIDDLEWARE / LOGGING.
"""
from ai_engine_adk import observability_logging as obs


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = obs.valid_id(request.META.get('HTTP_X_REQUEST_ID')) or obs.new_request_id('req')
        request.request_id = request_id
        tokens = obs.set_context(request_id=request_id, session_id=None)
        try:
            response = self.get_response(request)
        finally:
            obs.reset_context(tokens)
        response['X-Request-ID'] = request_id
        return response
