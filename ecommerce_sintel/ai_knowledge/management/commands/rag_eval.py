"""
HARDENING F6/C5 (2026-09-24) -- mide el MECANISMO de recuperacion y abstencion del RAG sobre un corpus SINTETICO.

Uso (en el contenedor de Django de DESARROLLO, con el proveedor de embeddings real configurado):
    python manage.py rag_eval [--k 5] [--json ruta.json] [--keep]

Siembra los documentos de `ai_knowledge/eval_data.py` (source='synthetic-eval', app_name='eval_synth'), los embebe con el modelo activo,
ejecuta las consultas contra `RetrievalService` (el mismo codigo que usa /chat) y borra los datos sinteticos al terminar. No toca
documentos reales y NUNCA debe ejecutarse contra produccion.

Metricas: recall@1/3/k y MRR por segmento; abstencion correcta (preguntas fuera de dominio y adversariales con mejor similitud por
debajo de MIN_ANSWERABLE_SIMILARITY) y falsa abstencion (preguntas de dominio que el ADK responderia "sin informacion"). Los umbrales de
aceptacion se fijan DESPUES de tener este baseline (plan sec. 14.3); esto no es un gate.
"""
import json
import statistics
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from ai_knowledge.eval_data import ADVERSARIAL, DOCS, OUT_OF_DOMAIN
from ai_knowledge.models import AIKnowledgeDocument
from ai_knowledge.services.commands import AIKnowledgeDocumentCommands, AIKnowledgeEmbeddingCommands
from ai_knowledge.services.selectors import RetrievalService

APP = 'eval_synth'
SOURCE = 'synthetic-eval'


def _min_answerable() -> float:
    try:
        from ai_engine_adk.sintel_rag_adapter import MIN_ANSWERABLE_SIMILARITY
        return MIN_ANSWERABLE_SIMILARITY
    except Exception:  # noqa: BLE001
        return 0.35


class Command(BaseCommand):
    help = 'Mide recall@k / MRR / abstencion del RAG sobre un corpus sintetico (solo desarrollo).'

    def add_arguments(self, parser):
        parser.add_argument('--k', type=int, default=5)
        parser.add_argument('--json', dest='json_path', default='')
        parser.add_argument('--keep', action='store_true', help='No borrar el corpus sintetico al terminar.')

    def handle(self, *args, **opts):
        if not settings.DEBUG and not getattr(settings, 'ALLOW_RAG_EVAL', False):
            raise CommandError('rag_eval solo corre con DEBUG=True (desarrollo); no ejecutar contra produccion.')
        k = opts['k']
        threshold = _min_answerable()
        AIKnowledgeDocument.objects.filter(source=SOURCE).delete()
        try:
            for d in DOCS:
                doc = AIKnowledgeDocumentCommands.upsert_document(
                    title=d['title'], content=d['content'], app_name=APP, source=SOURCE,
                    visibility=AIKnowledgeDocument.VISIBILITY_PUBLIC, authority=AIKnowledgeDocument.AUTHORITY_INTERNAL,
                )
                assert doc.review_status == AIKnowledgeDocument.REVIEW_APPROVED, d['key']
            res = AIKnowledgeEmbeddingCommands.embed_pending_chunks(limit=500)
            self.stdout.write(f'embeddings: {res}')

            per_segment = defaultdict(lambda: {'n': 0, 'r1': 0, 'r3': 0, 'rk': 0, 'rr': 0.0, 'false_abstain': 0})
            top_sims_domain, misses = [], []
            for d in DOCS:
                for q in d['queries']:
                    results = RetrievalService.retrieve_public_knowledge(q, app_names=[APP], k=k)
                    titles = []
                    for r in results:
                        if r['title'] not in titles:
                            titles.append(r['title'])
                    rank = titles.index(d['title']) + 1 if d['title'] in titles else None
                    seg = per_segment[d['segment']]
                    seg['n'] += 1
                    seg['r1'] += bool(rank == 1)
                    seg['r3'] += bool(rank and rank <= 3)
                    seg['rk'] += bool(rank and rank <= k)
                    seg['rr'] += (1.0 / rank) if rank else 0.0
                    best_sim = (1.0 - min(r['distance'] for r in results)) if results else -1.0
                    top_sims_domain.append(best_sim)
                    if best_sim < threshold:
                        seg['false_abstain'] += 1
                    if not rank or rank > 1:
                        misses.append((q, d['title'], rank))

            def sims(queries):
                out = []
                for q in queries:
                    results = RetrievalService.retrieve_public_knowledge(q, app_names=[APP], k=k)
                    out.append((1.0 - min(r['distance'] for r in results)) if results else -1.0)
                return out

            ood_sims, adv_sims = sims(OUT_OF_DOMAIN), sims(ADVERSARIAL)
            abst_ood = sum(s < threshold for s in ood_sims)
            abst_adv = sum(s < threshold for s in adv_sims)

            total = sum(s['n'] for s in per_segment.values())
            summary = {
                'k': k, 'threshold_min_answerable': threshold, 'docs': len(DOCS), 'in_domain_cases': total,
                'ood_cases': len(OUT_OF_DOMAIN), 'adversarial_cases': len(ADVERSARIAL),
                'recall@1': round(sum(s['r1'] for s in per_segment.values()) / total, 3),
                'recall@3': round(sum(s['r3'] for s in per_segment.values()) / total, 3),
                f'recall@{k}': round(sum(s['rk'] for s in per_segment.values()) / total, 3),
                'mrr': round(sum(s['rr'] for s in per_segment.values()) / total, 3),
                'false_abstention': round(sum(s['false_abstain'] for s in per_segment.values()) / total, 3),
                'abstention_ood': f'{abst_ood}/{len(OUT_OF_DOMAIN)}',
                'abstention_adversarial': f'{abst_adv}/{len(ADVERSARIAL)}',
                'sim_in_domain_median': round(statistics.median(top_sims_domain), 3),
                'sim_in_domain_min': round(min(top_sims_domain), 3),
                'sim_in_domain_p10': round(sorted(top_sims_domain)[max(int(len(top_sims_domain) * 0.1) - 1, 0)], 3),
                'sim_ood_median': round(statistics.median(ood_sims), 3),
                'sim_ood_max': round(max(ood_sims), 3),
                'sim_adversarial_max': round(max(adv_sims), 3),
                'per_segment': {seg: {'n': v['n'], 'recall@1': round(v['r1'] / v['n'], 2), 'mrr': round(v['rr'] / v['n'], 2)}
                                for seg, v in sorted(per_segment.items())},
                'misses_top1': [{'query': q, 'expected': t, 'rank': r} for q, t, r in misses],
            }
            self.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
            if opts['json_path']:
                with open(opts['json_path'], 'w', encoding='utf-8') as fh:
                    json.dump(summary, fh, ensure_ascii=False, indent=2)
        finally:
            if not opts['keep']:
                deleted = AIKnowledgeDocument.objects.filter(source=SOURCE).delete()
                self.stdout.write(f'corpus sintetico borrado: {deleted}')
