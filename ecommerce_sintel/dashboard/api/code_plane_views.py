"""
dashboard/api/code_plane_views.py -- plano de codigo controlado para el MCP (plan MCP, FASE 7-8, 2026-09-25). SOLO DESARROLLO.

Envuelve `ai_editor` SIN reimplementar nada: analisis por grafo (solo lectura), propuesta en sandbox (`run_autonomous_change_loop`, nunca escribe el workspace),
decision humana, promocion por `promote_to_workspace()` (5 compuertas + F22) y rollback. Apagado por defecto: `AI_EDITOR_CODE_PLANE_ENABLED` (404 si esta apagado).

Fronteras:
- La DECISION (aprobar/rechazar) SOLO la toma un admin con sesion normal: un JWT canjeado por el MCP (claim via=mcp) recibe 403.
- Promover exige decision APPROVE previa de un humano + confirm=true; el MCP puede pedir la promocion (perfil CODE_CHANGE) pero nunca aprobarla.
- Nada de esto ejecuta tests: devuelve los que hay que correr manualmente.
"""
import logging

from django.conf import settings
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.api.views import ADMIN_PERMISSIONS
from security.services.mcp_tokens import is_mcp_authenticated

logger = logging.getLogger(__name__)


def _require_enabled() -> None:
    if not getattr(settings, 'AI_EDITOR_CODE_PLANE_ENABLED', False):
        raise NotFound('CODE_PLANE_DISABLED')


def _audit(request, action: str, **meta) -> None:
    try:
        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands
        SecurityCommands.log_event(SecurityEvent.MCP_ACTION, request=request, user=request.user,
                                   metadata={'event': 'code_' + action, 'via_mcp': is_mcp_authenticated(request),
                                             **{k: str(v)[:200] for k, v in meta.items()}})
    except Exception:  # noqa: BLE001 - la auditoria durable nunca rompe la operacion
        logger.exception('code plane audit failed')


class _CodePlaneView(APIView):
    permission_classes = ADMIN_PERMISSIONS

    def initial(self, request, *args, **kwargs):
        _require_enabled()
        super().initial(request, *args, **kwargs)


def _text(request, name: str, max_len: int = 300) -> str:
    value = str(request.query_params.get(name, '')).strip()
    if not value or len(value) > max_len or '\x00' in value:
        raise ValidationError({name: 'requerido (max %d caracteres, sin bytes nulos)' % max_len})
    return value


class CodeAnalysisView(_CodePlaneView):
    """GET /api/v1/dashboard/code/analysis/?op=symbol|references|impact|resolve|tests|context|status&q=... -- lectura por grafo."""

    def get(self, request):
        from ai_editor import graph_client as g
        op = request.query_params.get('op', '')
        if op == 'status':
            return Response({'op': op, 'result': g.get_graph_status()})
        q = _text(request, 'q')
        table = {'symbol': g.find_symbol, 'references': g.find_consumers, 'impact': g.calculate_impact,
                 'resolve': g.resolve_change, 'tests': g.find_tests, 'context': g.build_context_packet}
        if op not in table:
            raise ValidationError({'op': 'valores: status, ' + ', '.join(sorted(table))})
        try:
            result = table[op](q)
        except Exception as exc:  # noqa: BLE001
            logger.warning('code analysis %s failed: %s', op, type(exc).__name__)
            return Response({'error': 'ANALYSIS_FAILED', 'detail': type(exc).__name__}, status=status.HTTP_502_BAD_GATEWAY)
        _audit(request, 'analysis', op=op)
        return Response({'op': op, 'query': q, 'result': result})


class CodeProposalListCreateView(_CodePlaneView):
    """GET lista propuestas del proceso; POST {request} genera una propuesta EN SANDBOX (usa el LLM configurado; puede tardar)."""

    def get(self, request):
        from ai_editor import change_store as cs
        return Response({'results': [cs.summarize(e) for e in cs.list_entries()]})

    def post(self, request):
        from ai_editor import change_store as cs
        from ai_editor.agent.loop import run_autonomous_change_loop
        text = str(request.data.get('request', '')).strip()
        if len(text) < 10 or len(text) > 2000:
            raise ValidationError({'request': 'entre 10 y 2000 caracteres'})
        run = run_autonomous_change_loop(text)
        entry = cs.put(request.user.id, text, run, via_mcp=is_mcp_authenticated(request))
        _audit(request, 'propose', change_id=entry.change_id, pipeline_status=getattr(run, 'status', ''))
        return Response(cs.summarize(entry, full=True), status=status.HTTP_201_CREATED)


def _entry_or_404(change_id: str):
    from ai_editor import change_store as cs
    entry = cs.get(change_id)
    if entry is None:
        raise Http404
    return entry


class CodeProposalDetailView(_CodePlaneView):
    """GET detalle completo (reportes de validacion, riesgo, tests requeridos, texto de revision). DELETE descarta y limpia el sandbox."""

    def get(self, request, change_id):
        from ai_editor import change_store as cs
        return Response(cs.summarize(_entry_or_404(change_id), full=True))

    def delete(self, request, change_id):
        from ai_editor import change_store as cs
        _entry_or_404(change_id)
        cs.discard(change_id)
        _audit(request, 'discard', change_id=change_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CodeProposalDecisionView(_CodePlaneView):
    """POST {decision: APPROVE|REJECT|..., note, security_review_acknowledged}. SOLO humano: un JWT via=mcp recibe 403."""

    def post(self, request, change_id):
        from ai_editor import change_store as cs
        from ai_editor.approval.gate import record_decision
        if is_mcp_authenticated(request):
            _audit(request, 'decision_denied', change_id=change_id)
            raise PermissionDenied('Un cliente MCP no puede aprobar ni rechazar cambios de codigo: la decision es de un administrador humano.')
        entry = _entry_or_404(change_id)
        if cs.state_of(entry) not in ('PROPOSED', 'APPROVED', 'REJECTED'):
            raise ValidationError({'detail': 'La propuesta no esta en un estado que admita decision (%s).' % cs.state_of(entry)})
        try:
            approval = record_decision(str(request.data.get('decision', '')).upper(), reviewer_note=str(request.data.get('note', ''))[:1000] or None,
                                       security_review_acknowledged=bool(request.data.get('security_review_acknowledged', False)))
        except ValueError as exc:
            raise ValidationError({'decision': str(exc)})
        entry.approval, entry.approved_by = approval, request.user.id
        _audit(request, 'decision', change_id=change_id, decision=approval.decision, security_ack=approval.security_review_acknowledged)
        return Response(cs.summarize(entry))


class CodeProposalPromoteView(_CodePlaneView):
    """POST {confirm: true}: promueve al workspace SOLO si un humano registro APPROVE y las compuertas de ai_editor pasan."""

    def post(self, request, change_id):
        from ai_editor import change_store as cs
        from ai_editor.repository.promote import promote_to_workspace
        from ai_editor.workspace import WORKSPACE_ROOT
        entry = _entry_or_404(change_id)
        loop = entry.sandbox_result
        if loop is None or not loop.ready_for_approval:
            raise ValidationError({'detail': 'La propuesta no quedo lista para aprobacion; no hay nada que promover.'})
        if entry.approval is None:
            raise ValidationError({'detail': 'NOT_APPROVED: falta la decision humana APPROVE (POST .../decision/ con sesion de administrador).'})
        if entry.promote_result is not None and entry.promote_result.status == 'PROMOTED':
            raise ValidationError({'detail': 'La propuesta ya fue promovida.'})
        result = promote_to_workspace(loop.sandbox, entry.approval, WORKSPACE_ROOT, confirm=request.data.get('confirm') is True,
                                      validation_report=loop.validation_report)
        if result.status == 'PROMOTED':
            entry.promote_result = result
        _audit(request, 'promote', change_id=change_id, result=result.status, files=len(result.files_promoted))
        body = cs.summarize(entry)
        body['promote_status'] = result.status
        body['promote_detail'] = result.detail
        return Response(body, status=status.HTTP_200_OK if result.status == 'PROMOTED' else status.HTTP_409_CONFLICT)


class CodeProposalRollbackView(_CodePlaneView):
    """POST {confirm: true}: restaura los archivos previos de una promocion hecha en este proceso."""

    def post(self, request, change_id):
        from ai_editor import change_store as cs
        from ai_editor.repository.rollback import rollback_promotion
        from ai_editor.workspace import WORKSPACE_ROOT
        entry = _entry_or_404(change_id)
        if request.data.get('confirm') is not True:
            raise ValidationError({'confirm': 'confirm=true es obligatorio'})
        result = rollback_promotion(WORKSPACE_ROOT, entry.promote_result)
        if result.status == 'ROLLED_BACK':
            entry.rolled_back = True
        _audit(request, 'rollback', change_id=change_id, result=result.status)
        body = cs.summarize(entry)
        body['rollback'] = result.to_dict()
        return Response(body)
