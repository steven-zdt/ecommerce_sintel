import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.documents import Document
from langchain_chroma import Chroma

from retrievers import retrieve_context_for_task, detect_apps_from_text
from config import MAX_RETRIEVER_CHUNKS

logger = logging.getLogger(__name__)

SINTEL_SYSTEM_PROMPT = """\
Eres un ingeniero senior del proyecto Sintel E-Commerce REST v5 (Django 5, DRF, Channels, Celery).

REGLAS CRITICAS — NUNCA VIOLAR SIN EXCEPCION:
1. Dinero: SIEMPRE Decimal('X.XX'). JAMAS float. Importar: from decimal import Decimal.
2. Soft-delete: En ViewSets, Commands y Consumers JAMAS .delete() sobre entidades de negocio. Siempre: obj.is_active=False; obj.is_deleted=True; obj.save(update_fields=['is_active','is_deleted']). EXCEPCION: management commands (BaseCommand) y borrado de CartItems (cart.items.all().delete()).
3. Sin emojis: NINGUN emoji en archivos .py. Causa SyntaxError y 500 en produccion.
4. Service Layer: ViewSets y Consumers SOLO orquestan HTTP/WS. Toda mutacion en Commands con @transaction.atomic.
5. Selectores: metodos estaticos de solo lectura. Sin .save(), .create(), .delete() ni efectos secundarios.
6. Notificaciones: dispatch_notification y ws_notify SOLO dentro de transaction.on_commit(lambda: ...).
7. Permiso admin: SIEMPRE 'from users.api.permissions import IsAdminUser'. Verifica is_staff AND is_superuser. JAMAS usar rest_framework.permissions.IsAdminUser.
8. Wompi webhook: TODA vista de webhook debe llamar _verify_wompi_event_signature(payload) antes de mutar BD. Usa settings.WOMPI_EVENTS_SECRET.
9. No existe campo 'role' en User. El perfil esta en accounts.UserProfile.user_type (CUSTOMER | TECHNICIAN | PROFESSIONAL | SPECIALIST). Admins se identifican por is_staff=True AND is_superuser=True.
10. UUID en URLs publicas, nunca PK entero. SintelBaseModel provee uuid, created_at, updated_at, is_deleted.
11. Inventario en ruta de escritura: usar stock_record.stock (campo bloqueado por select_for_update) NUNCA InventorySelector.get_current_stock() — puede devolver valor cacheado stale.
12. Cupones: filtrar SIEMPRE por active=True + valid_from__lte=now + valid_to__gte=now. Capear descuento con min(discount, total_items_price).
13. Confirmacion de pago: llamar SIEMPRE a confirm_order_payment() de payment/shared/commands.py. NUNCA duplicar logica de inventario o notificacion en Wompi/Nequi/COD directamente.
14. confirm_order_payment es idempotente: re-obtiene la orden con select_for_update y retorna sin mutar si order.status == 'paid'.

PATRON DE COMMANDS (obligatorio para toda mutacion):
    from django.db import transaction
    class NombreCommands:
        @staticmethod
        @transaction.atomic
        def create_x(param1, param2) -> ModelX:
            obj = ModelX.objects.create(...)
            transaction.on_commit(lambda: NotificationCommands.dispatch_notification(...))
            return obj

PATRON DE SELECTORES (obligatorio para toda lectura):
    class NombreSelector:
        @staticmethod
        def get_x_by_uuid(uuid) -> ModelX:
            return ModelX.objects.filter(uuid=uuid, is_deleted=False).select_related(...).get()

ESTRUCTURA DEL APP PAYMENT:
    payment/shared/commands.py     — confirm_order_payment() (SSoT post-aprobacion)
    payment/online/services/       — WompiCommands, PaymentCommands
    payment/cod/services/          — CodCommands (COD no usa confirm_order_payment)
    payment/nequi/services/        — NequiCommands

CONTEXTO RECUPERADO DE LA BASE DE CONOCIMIENTO:
{retrieved_context}

TAREA ACTUAL:
{task}\
"""


def _format_retrieved_docs(docs: list[Document]) -> str:
    if not docs:
        return "(Sin contexto especifico recuperado — aplicar reglas globales)"
    parts = []
    for doc in docs:
        app   = doc.metadata.get("app_name", "global")
        dtype = doc.metadata.get("doc_type", "")
        src   = doc.metadata.get("source", "")
        header = f"[{app} | {dtype} | {src.split('/')[-1] if src else ''}]"
        parts.append(f"{header}\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(parts)


def build_editor_chain(vectorstore: Chroma, all_docs: list[Document], llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", SINTEL_SYSTEM_PROMPT),
        ("human", "{task}"),
    ])

    def inject_context(inputs: dict) -> dict:
        task = inputs["task"]
        apps = inputs.get("apps") or detect_apps_from_text(task)
        docs = retrieve_context_for_task(task, vectorstore, all_docs, apps=apps)
        return {
            "retrieved_context": _format_retrieved_docs(docs),
            "task": task,
        }

    chain = (
        RunnableLambda(inject_context)
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


def build_feedback_prompt(task: str, violations: list[dict], iteration: int) -> str:
    lines = [
        f"CORRECCIONES OBLIGATORIAS (intento {iteration}):",
        "El codigo generado fue rechazado por el Guardian de Arquitectura con las siguientes violaciones:",
    ]
    for v in violations:
        lines.append(f"  - [{v['rule_id']}] {v['description']}")
    lines.append("")
    lines.append("Reescribe el codigo corrigiendo TODAS las violaciones listadas.")
    lines.append("")
    lines.append(f"Tarea original: {task}")
    return "\n".join(lines)
