"""
HARDENING F17/C2 -- compara el motor CANARY contra el STABLE con las metricas reales de los ultimos N horas.

    python manage.py ai_canary_report --hours 24 [--min-turns 30] [--json]

Solo lectura sobre ChatMessage.ai_metrics (la clave `engine_track` la escribe support/services/ai_bridge.py). Reutiliza
ChatAnalyticsSelector.summarize_observability (F9): p50/p95/p99, degradacion, fallback de proveedor, tokens, banderas de seguridad.
Veredicto SUGERIDO (no automatico): HOLD (pocos datos) / ROLLBACK (degradacion, latencia o seguridad peor) / PROCEED.
No imprime contenido de conversaciones. LO EJECUTA EL USUARIO (el asistente no corre comandos de prueba).
"""
import json
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from support.models import ChatMessage
from support.services.selectors import ChatAnalyticsSelector

SECURITY_PREFIXES = ('blocked_', 'secret_')


def _split_by_track(rows: list) -> dict:
    tracks = {'stable': [], 'canary': []}
    for m in rows:
        if isinstance(m, dict):
            tracks['canary' if m.get('engine_track') == 'canary' else 'stable'].append(m)
    return tracks


def _summary(metrics_list: list) -> dict:
    summary = ChatAnalyticsSelector.summarize_observability(metrics_list)
    turns = sum(1 for m in metrics_list if not m.get('engine_unavailable'))
    handoffs = sum(1 for m in metrics_list if m.get('handoff'))
    security = sum(
        1 for m in metrics_list
        if any(str(f).startswith(SECURITY_PREFIXES) for f in (m.get('output_flags') or [])) or (m.get('injection_flags') or [])
    )
    summary.update({
        'attempts': len(metrics_list), 'turns_ok': turns,
        'handoff_rate': round(handoffs / turns, 4) if turns else 0.0,
        'security_flag_turns': security,
        'security_flag_rate': round(security / len(metrics_list), 4) if metrics_list else 0.0,
    })
    return summary


def verdict(stable: dict, canary: dict, *, min_turns: int, max_degraded_delta: float, max_p95_ratio: float,
            max_security_delta: float) -> tuple[str, list[str]]:
    reasons = []
    if canary['attempts'] < min_turns:
        return 'HOLD', [f"canary con {canary['attempts']} turnos (< {min_turns}): faltan datos"]
    if canary['degraded_rate'] - stable['degraded_rate'] > max_degraded_delta:
        reasons.append(f"degradacion canary {canary['degraded_rate']:.2%} vs stable {stable['degraded_rate']:.2%}")
    sp, cp = stable.get('p95_duration_ms'), canary.get('p95_duration_ms')
    if sp and cp and cp / sp > max_p95_ratio:
        reasons.append(f"p95 canary {cp} ms vs stable {sp} ms (x{cp / sp:.2f})")
    if canary['security_flag_rate'] - stable['security_flag_rate'] > max_security_delta:
        reasons.append(f"banderas de seguridad canary {canary['security_flag_rate']:.2%} vs stable {stable['security_flag_rate']:.2%}")
    if canary['provider_fallback_rate'] - stable['provider_fallback_rate'] > 0.05:
        reasons.append('el canary cae mas al proveedor de respaldo')
    return ('ROLLBACK', reasons) if reasons else ('PROCEED', ['sin regresion frente a stable en las metricas medidas'])


class Command(BaseCommand):
    help = 'Compara canary vs stable (latencia, degradacion, fallback, seguridad) y sugiere HOLD / PROCEED / ROLLBACK.'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=24)
        parser.add_argument('--min-turns', type=int, default=30, help='turnos minimos del canary para decidir')
        parser.add_argument('--max-degraded-delta', type=float, default=0.02)
        parser.add_argument('--max-p95-ratio', type=float, default=1.3)
        parser.add_argument('--max-security-delta', type=float, default=0.01)
        parser.add_argument('--json', action='store_true')

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=max(1, options['hours']))
        rows = list(ChatMessage.objects.filter(ai_metrics__isnull=False, created_at__gte=cutoff, is_deleted=False)
                    .values_list('ai_metrics', flat=True))
        tracks = _split_by_track(rows)
        stable, canary = _summary(tracks['stable']), _summary(tracks['canary'])
        decision, reasons = verdict(
            stable, canary, min_turns=options['min_turns'], max_degraded_delta=options['max_degraded_delta'],
            max_p95_ratio=options['max_p95_ratio'], max_security_delta=options['max_security_delta'])
        report = {'window_hours': options['hours'], 'stable': stable, 'canary': canary, 'verdict': decision, 'reasons': reasons}
        if options['json']:
            self.stdout.write(json.dumps(report, indent=2, sort_keys=True, default=str))
            return
        out = self.stdout.write
        out('Canary vs stable -- ultimas %d h' % options['hours'])
        for name, s in (('stable', stable), ('canary', canary)):
            out('  %-6s intentos=%s ok=%s degradado=%.2f%% p50=%s p95=%s fallback_prov=%.2f%% handoff=%.2f%% seguridad=%.2f%% tokens_out=%s' % (
                name, s['attempts'], s['turns_ok'], s['degraded_rate'] * 100, s['p50_duration_ms'], s['p95_duration_ms'],
                s['provider_fallback_rate'] * 100, s['handoff_rate'] * 100, s['security_flag_rate'] * 100, s['tokens_out_total']))
        out('VEREDICTO SUGERIDO: %s' % decision)
        for r in reasons:
            out('  - %s' % r)
