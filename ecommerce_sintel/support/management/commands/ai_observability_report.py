"""
HARDENING F9/C4 -- reporte de observabilidad del asistente (fuente de las metricas de F0 sec. 4.4 y de los SLO de F24).

Uso: python manage.py ai_observability_report --days 7 [--json]

Solo lectura: agrega ChatMessage.ai_metrics con ChatAnalyticsSelector (sin infraestructura nueva). No imprime contenido de
conversaciones. TTFT no existe: /chat no hace streaming.
"""
import json

from django.core.management.base import BaseCommand

from support.services.selectors import ChatAnalyticsSelector


class Command(BaseCommand):
    help = 'Reporte de latencia, degradacion, fallback, tokens y banderas de seguridad del asistente de IA.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='Ventana en dias (default 7).')
        parser.add_argument('--json', action='store_true', help='Salida JSON en vez de texto.')

    def handle(self, *args, **options):
        days = max(1, options['days'])
        summary = ChatAnalyticsSelector.get_summary(days=days)
        if options['json']:
            self.stdout.write(json.dumps(summary, indent=2, sort_keys=True, default=str))
            return
        out = self.stdout.write
        out('Observabilidad del asistente -- ultimos %d dias' % days)
        out('  turnos IA: %s | conversaciones: %s | CSAT: %s' % (
            summary['total_ai_turns'], summary['total_conversations'], summary['avg_csat']))
        out('  latencia ms  p50=%s p95=%s p99=%s (media %s)' % (
            summary['p50_duration_ms'], summary['p95_duration_ms'], summary['p99_duration_ms'], summary['avg_duration_ms']))
        out('  degradados: %s (%.2f%%) | fallback de proveedor: %.2f%% | handoff: %.2f%%' % (
            summary['engine_unavailable_count'], summary['degraded_rate'] * 100,
            summary['provider_fallback_rate'] * 100, summary['handoff_rate'] * 100))
        out('  proveedores: %s' % (', '.join('%s=%s' % (p['provider'], p['count']) for p in summary['provider_breakdown']) or '-'))
        out('  tools: total=%s, por turno=%s | rate limited=%s' % (
            summary['tool_calls_total'], summary['avg_tool_calls_per_turn'], summary['rate_limited_count']))
        out('  tokens: entrada=%s salida=%s' % (summary['tokens_in_total'], summary['tokens_out_total']))
        out('  banderas de inyeccion: %s' % (summary['injection_flag_counts'] or '-'))
        out('  banderas de salida: %s' % (summary['output_flag_counts'] or '-'))
