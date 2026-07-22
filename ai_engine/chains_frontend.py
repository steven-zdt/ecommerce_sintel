import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_core.documents import Document
from langchain_chroma import Chroma

from retrievers import retrieve_context_for_task, detect_apps_from_text
from config import MAX_RETRIEVER_CHUNKS

logger = logging.getLogger(__name__)

SINTEL_FRONTEND_PROMPT = """\
Eres un ingeniero senior de frontend del proyecto Sintel E-Commerce (Vue 3, Vite, Pinia, Bootstrap 5).

REGLAS CRITICAS — NUNCA VIOLAR:

1. SCRIPT SETUP SIEMPRE: Todo componente usa <script setup>. NUNCA Options API (export default { data() {}, methods: {} }).

2. HTTP SIEMPRE POR useApi: NUNCA 'import axios from axios' directo en componentes.
   const api = useApi()
   const { data } = await api.get('shop/products/')

3. ENDPOINTS — REGLA CRITICA:
   - LECTURA (GET)  → endpoints PUBLICOS: shop/products/, renting/equipment/, technical_services/services/
   - ESCRITURA (POST/PATCH/DELETE) → SIEMPRE dashboard/: dashboard/products/, dashboard/categories/, etc.
   Los ViewSets publicos son ReadOnly — POST retorna 405.

4. LOOKUP FIELDS:
   - FK en payload → item.uuid (NO item.id)
   - URL de escritura → item.id (PK entero): dashboard/products/${item.id}/
   - v-for :key → item.uuid

5. CRUD CON OFFCANVAS:
   const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas()
   <SintelOffcanvas v-model="show" title="..." width="560px">
     <XxxForm :item="selected" :mode="mode" @success="fetchItems(); close()" @cancel="close()" />
   </SintelOffcanvas>

6. CONFIRMACION DE BORRADO — siempre fila inline, NUNCA modal flotante:
   <template v-if="pendingDelete?.uuid === item.uuid">
     <td colspan="99" class="bg-danger-subtle p-2">
       ¿Desactivar {{ item.name }}?
       <button class="btn btn-sm btn-danger" @click="executeDelete(item)">Confirmar</button>
       <button class="btn btn-sm btn-secondary" @click="pendingDelete = null">Cancelar</button>
     </td>
   </template>

7. TOASTS: SIEMPRE useToast() — NUNCA alert() ni console.log para mensajes al usuario.
   const { toast } = useToast()
   toast.success('Guardado'), toast.error('Error'), toast.info('...'), toast.warning('...')

8. TRY/CATCH OBLIGATORIO en toda llamada async:
   try {
     const { data } = await api.get('...')
   } catch (err) {
     toast.error(err.response?.data?.detail || 'Error al cargar')
   }

9. DEBOUNCE en busqueda (400ms minimo):
   let timer = null
   function onSearch() { clearTimeout(timer); timer = setTimeout(fetchItems, 400) }

10. LAZY LOADING en router:
    { path: '/ruta', component: () => import('@/modules/shop/ProductList.vue') }

11. IMPORTS VALIDOS: SOLO importar de FRONTEND_COMPONENT_REGISTRY.md.
    NO inventar: Button, Badge, Modal, Spinner, Card, Drawer, Rating, Input, Table.
    Para spinner usar: <div class="spinner-border text-primary"></div>

12. SIN TYPESCRIPT: Solo JavaScript puro. Sin type annotations, sin interfaces, sin .ts.

13. BOOTSTRAP 5: Clases BS5 para layout/UI. Iconos Bootstrap Icons: <i class="bi bi-pencil"></i>

14. PRECIOS: new Intl.NumberFormat('es-CO').format(num) — NUNCA toFixed(2) ni Math.round.

15. STORES GLOBALES EXISTENTES UNICAMENTE:
    useAuthStore() → @/store/auth (tokens, user, isAdmin, isAuthenticated)
    useAppConfigStore() → @/store/appConfig (brand, navbar)
    useCartStore() → @/store/cart (items, total, count)
    NO crear stores nuevos sin instruccion explicita.

PATRON COMPLETO CRUD — MODULO ADMIN:
<template>
  <div>
    <div class="d-flex justify-content-between mb-3">
      <input v-model="search" @input="onSearch" class="form-control w-auto" placeholder="Buscar...">
      <button class="btn btn-primary" @click="openCreate()"><i class="bi bi-plus-circle me-1"></i>Nuevo</button>
    </div>

    <div v-if="loading" class="d-flex justify-content-center py-4">
      <div class="spinner-border text-primary"></div>
    </div>

    <table v-else class="table table-hover table-sm">
      <thead class="table-dark">
        <tr><th>Nombre</th><th>Estado</th><th></th></tr>
      </thead>
      <tbody>
        <template v-for="item in items" :key="item.uuid">
          <tr v-if="pendingDelete?.uuid === item.uuid" class="bg-danger-subtle">
            <td colspan="99" class="p-2">
              ¿Desactivar "{{ item.name }}"?
              <button class="btn btn-sm btn-danger ms-2" @click="executeDelete(item)">Confirmar</button>
              <button class="btn btn-sm btn-secondary ms-1" @click="pendingDelete = null">Cancelar</button>
            </td>
          </tr>
          <tr v-else>
            <td>{{ item.name }}</td>
            <td><span :class="item.is_active ? 'badge bg-success' : 'badge bg-secondary'">{{ item.is_active ? 'Activo' : 'Inactivo' }}</span></td>
            <td class="text-end">
              <button class="btn btn-sm btn-outline-primary me-1" @click="openEdit(item)"><i class="bi bi-pencil"></i></button>
              <button class="btn btn-sm btn-outline-danger" @click="pendingDelete = item"><i class="bi bi-trash"></i></button>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <SintelOffcanvas v-model="show" :title="mode === 'create' ? 'Nuevo Item' : 'Editar Item'" width="560px">
      <ItemForm :item="selected" :mode="mode" @success="fetchItems(); close()" @cancel="close()" />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { useOffcanvas } from '@/composables/useOffcanvas'
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue'
import ItemForm from './ItemForm.vue'

const api = useApi()
const { toast } = useToast()
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas()

const items = ref([])
const loading = ref(false)
const search = ref('')
const pendingDelete = ref(null)
let debounceTimer = null

onMounted(fetchItems)

function onSearch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchItems, 400)
}

async function fetchItems() {
  loading.value = true
  try {
    const { data } = await api.get('shop/products/', { params: { search: search.value } })
    items.value = data.results ?? data
  } catch (err) {
    toast.error(err.response?.data?.detail || 'Error al cargar')
  } finally {
    loading.value = false
  }
}

async function executeDelete(item) {
  try {
    await api.patch(`dashboard/products/${item.id}/`, { is_active: false })
    toast.success('Desactivado correctamente')
    pendingDelete.value = null
    fetchItems()
  } catch (err) {
    toast.error('Error al desactivar')
  }
}
</script>

CONTEXTO RECUPERADO DE LA BASE DE CONOCIMIENTO:
{retrieved_context}

TAREA ACTUAL:
{task}\
"""

FRONTEND_APP_LAYER_MAP = {
    "shop":               "frontend/src/modules/shop",
    "renting":            "frontend/src/modules/renting",
    "technical_services": "frontend/src/modules/technical_services",
    "orders":             "frontend/src/modules/orders",
    "inventory":          "frontend/src/modules/inventory",
    "quotes":             "frontend/src/modules/quotes",
    "users":              "frontend/src/modules/users",
    "core":               "frontend/src/modules/core",
    "marketing":          "frontend/src/modules/marketing",
    "support":            "frontend/src/modules/support",
    "customer":           "frontend/src/views/customer",
    "landing":            "frontend/src/components/ui/landing",
}


def _format_retrieved_docs(docs: list[Document]) -> str:
    if not docs:
        return "(Sin contexto especifico recuperado — aplicar reglas globales de frontend)"
    parts = []
    for doc in docs:
        app   = doc.metadata.get("app_name", "global")
        dtype = doc.metadata.get("doc_type", "")
        src   = doc.metadata.get("source", "")
        fname = src.replace("\\", "/").split("/")[-1] if src else ""
        header = f"[{app} | {dtype} | {fname}]"
        parts.append(f"{header}\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(parts)


def build_frontend_chain(vectorstore: Chroma, all_docs: list[Document], llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", SINTEL_FRONTEND_PROMPT),
        ("human", "{task}"),
    ])

    def inject_frontend_context(inputs: dict) -> dict:
        task = inputs["task"]
        apps = inputs.get("apps") or detect_apps_from_text(task)

        # Priorizar docs frontend (language=vue o skill de frontend)
        frontend_docs = [
            d for d in all_docs
            if d.metadata.get("language") in ("vue", "javascript")
            or d.metadata.get("doc_type") in ("frontend_spec", "skill")
            or "frontend" in d.metadata.get("source", "").replace("\\", "/").lower()
        ]

        # Si no hay suficientes docs frontend, completar con todos
        corpus = frontend_docs if len(frontend_docs) >= 5 else all_docs

        docs = retrieve_context_for_task(task, vectorstore, corpus, apps=apps)
        return {
            "retrieved_context": _format_retrieved_docs(docs),
            "task": task,
        }

    chain = (
        RunnableLambda(inject_frontend_context)
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


def build_frontend_feedback_prompt(task: str, violations: list[dict], iteration: int) -> str:
    lines = [
        f"CORRECCIONES OBLIGATORIAS — FRONTEND VUE (intento {iteration}):",
        "El codigo Vue generado fue rechazado por las siguientes violaciones:",
    ]
    for v in violations:
        lines.append(f"  - [{v['rule_id']}] {v['description']}")
    lines.append("")
    lines.append("Reescribe el componente Vue corrigiendo TODAS las violaciones.")
    lines.append("Recuerda: <script setup>, useApi(), dashboard/ para escrituras, uuid en FKs.")
    lines.append("")
    lines.append(f"Tarea original: {task}")
    return "\n".join(lines)
