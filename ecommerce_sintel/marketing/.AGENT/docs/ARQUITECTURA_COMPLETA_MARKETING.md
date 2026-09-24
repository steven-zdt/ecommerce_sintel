# ARQUITECTURA COMPLETA - MÓDULO MARKETING

## 📋 Descripción General

El módulo **Marketing** es el sistema central de inteligencia y automatización de campañas multicanal de la plataforma Sintel E-Commerce.

**Responsabilidades principales:**
- Gestión de campañas publicitarias multicanal (Email, WhatsApp, Facebook, Instagram, YouTube, TikTok, X, Google Business)
- Creación y distribución de ofertas relámpago (FlashOffer) con tiempo limitado
- Generación de ofertas personalizadas basadas en historial de clientes
- Análisis consolidado de datos de vendas para inteligencia de negocio
- **Marketing Intelligence Agent**: Sistema autónomo con LLM que analiza contexto y dispara campañas automáticas
- Orquestación asíncrona de envíos via Celery
- Auditoría completa de intentos de envío (CampaignLog)

**Arquitectura clave:**
- **Service Layer**: Commands (escritura), Selectors (lectura)
- **Channel Adapter Pattern**: Abstracción para múltiples canales de marketing
- **LLM Router**: Soporte para OpenAI, Anthropic (Claude), Google Gemini
- **Pull-based Data**: Integración sin acoplamiento directo con otros módulos
- **Async Dispatch**: Celery tasks con idempotencia garantizada

---

## 📁 Estructura de Directorios

```
marketing/
├── __init__.py
├── apps.py                          # Configuración de la app
├── models.py                        # FlashOffer, PersonalOffer, MarketingCampaign, CampaignLog, SalesAnalysis, AgentRun
├── admin.py                         # Django admin configuration
├── urls.py                          # Router raíz del módulo
├── tasks.py                         # Celery tasks
│
├── api/
│   ├── __init__.py
│   ├── views.py                     # ViewSets: Campaigns, FlashOffers, AgentRuns, Dashboard
│   ├── serializers.py               # Serializadores de entrada/salida
│   └── urls.py                      # Router REST con endpoints
│
├── services/
│   ├── __init__.py                  # Exports: Commands, Selectors
│   ├── commands.py                  # MarketingCommands (dispatch, send_now)
│   ├── selectors.py                 # MarketingSelector (queries, dashboard, user profiling)
│   └── meta_selectors.py            # [2026-08-31] MetaCampaignSelector — Meta Ads READ normalizado (FASE 7)
│
├── channels/
│   ├── __init__.py
│   ├── base.py                      # AbstractChannelAdapter (contract)
│   ├── registry.py                  # CHANNEL_REGISTRY, get_adapter()
│   ├── email_channel.py             # EmailChannelAdapter
│   ├── whatsapp_channel.py          # WhatsAppChannelAdapter
│   ├── facebook_channel.py          # FacebookChannelAdapter
│   ├── instagram_channel.py         # InstagramChannelAdapter
│   ├── youtube_channel.py           # YouTubeChannelAdapter
│   ├── tiktok_channel.py            # TikTokChannelAdapter
│   ├── x_channel.py                 # XChannelAdapter (Twitter)
│   └── google_business_channel.py   # GoogleBusinessChannelAdapter
│
├── agent/
│   ├── __init__.py
│   ├── brain.py                     # MarketingAgent (orchestrator)
│   ├── llm_router.py                # LLMRouter (OpenAI, Anthropic, Gemini support)
│   ├── prompts.py                   # System & analysis prompts
│   └── [tool use examples]
│
├── integrations/                    # [2026-08-31] Frontera HTTP hacia terceros
│   └── meta/                        # Frontera UNICA hacia Meta (Graph/WhatsApp/Marketing/CAPI)
│       ├── exceptions.py            # MetaApiError / *TransientError / *AuthError / *ConfigError / *RateLimitError
│       ├── client.py                # MetaGraphClient -- transporte puro (get/post/delete/paginate)
│       ├── signatures.py            # verify_meta_webhook_signature() -- funcion pura, fail-closed
│       ├── whatsapp.py              # MetaWhatsAppClient(send_template/send_text) sobre MetaGraphClient
│       ├── marketing.py             # MetaMarketingClient -- Marketing API READ (campaigns/adsets/ads/insights)
│       └── tests/                   # SimpleTestCase, mock de requests.request
│
└── migrations/
    ├── __init__.py
    ├── 0001_initial.py
    └── 0002_remove_marketingcampaign_channel_and_more.py
```

---

## 🏗️ Diagramas de Arquitectura

### Flujo de Capas (Layered Architecture)

```
┌──────────────────────────────────────────────────────────┐
│  CLIENTE (Dashboard Admin / API / Scheduled Agent)        │
└────────────────┬─────────────────────────────────────────┘
                 │
     ┌───────────▼──────────────────┐
     │   REST API (DRF)             │
     │  ViewSets + Routers          │
     └───────────┬──────────────────┘
                 │
     ┌───────────▼───────────────────────────────────────┐
     │   API Layer (api/views.py)                        │
     │  - MarketingCampaignViewSet                       │
     │  - FlashOfferViewSet                             │
     │  - AgentRunViewSet                               │
     │  - DashboardViewSet                              │
     └───────────┬───────────────────────────────────────┘
                 │
     ┌───────────▼───────────────────────────────────────┐
     │  Serializers (api/serializers.py)                │
     │  - MarketingCampaignSerializer                   │
     │  - FlashOfferSerializer                          │
     │  - AgentRunSerializer                            │
     │  - ConsolidatedDashboardSerializer               │
     └───────────┬───────────────────────────────────────┘
                 │
     ┌───────────▼──────────────────────────────────────────┐
     │   Business Logic Layer (services/ + agent/)          │
     │  ┌──────────────────────────────────────────────┐   │
     │  │ MarketingAgent (Brain)                       │   │
     │  │ - Gathers context from all apps             │   │
     │  │ - Calls LLM for reasoning                    │   │
     │  │ - Dispatches campaigns autonomously          │   │
     │  └──────────────────────────────────────────────┘   │
     │  ┌──────────────────────────────────────────────┐   │
     │  │ LLMRouter                                    │   │
     │  │ - Routes to OpenAI, Anthropic, or Gemini    │   │
     │  │ - Parses JSON responses                      │   │
     │  └──────────────────────────────────────────────┘   │
     │  ┌──────────────────────────────────────────────┐   │
     │  │ MarketingCommands (Write Operations)         │   │
     │  │ - dispatch() → Enqueue async tasks           │   │
     │  │ - send_now() → Execute per-channel send      │   │
     │  └──────────────────────────────────────────────┘   │
     │  ┌──────────────────────────────────────────────┐   │
     │  │ MarketingSelector (Read-only Queries)        │   │
     │  │ - get_consolidated_dashboard()               │   │
     │  │ - get_user_marketing_profile()               │   │
     │  │ - get_stale_stock_alerts()                   │   │
     │  └──────────────────────────────────────────────┘   │
     │  ┌──────────────────────────────────────────────┐   │
     │  │ Channel Adapters (registry.py)               │   │
     │  │ - EmailChannelAdapter                        │   │
     │  │ - WhatsAppChannelAdapter                     │   │
     │  │ - FacebookChannelAdapter                     │   │
     │  │ - InstagramChannelAdapter                    │   │
     │  │ - YouTubeChannelAdapter                      │   │
     │  │ - TikTokChannelAdapter                       │   │
     │  │ - XChannelAdapter                            │   │
     │  │ - GoogleBusinessChannelAdapter               │   │
     │  └──────────────────────────────────────────────┘   │
     └───────────┬──────────────────────────────────────────┘
                 │
     ┌───────────▼──────────────────────────────┐
     │   Celery Task Queue                      │
     │  - run_marketing_agent_task              │
     │  - send_via_channel_task (per channel)   │
     └───────────┬──────────────────────────────┘
                 │
     ┌───────────▼──────────────────────────────┐
     │   ORM Layer (Django Models)              │
     │  - MarketingCampaign                     │
     │  - CampaignLog (audit trail)             │
     │  - FlashOffer / PersonalOffer            │
     │  - SalesAnalysis (cache)                 │
     │  - AgentRun (execution log)              │
     └───────────┬──────────────────────────────┘
                 │
     ┌───────────▼──────────────────────────────┐
     │   External Services                      │
     │  - SendGrid (Email)                      │
     │  - Meta API (WhatsApp/Facebook/Ig)      │
     │  - YouTube API                           │
     │  - TikTok API                            │
     │  - X API v2                              │
     │  - Google Business Profile API           │
     │  - LLM APIs (OpenAI, Anthropic, Gemini) │
     │  - Database (PostgreSQL)                 │
     └──────────────────────────────────────────┘
```

### Flujo de Despacho de Campaña Manual

```
┌────────────────────────────────────────────┐
│  Admin crea campaña en dashboard            │
│  POST /api/v1/marketing/campaigns/          │
└────────┬─────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│  MarketingCampaignViewSet.create()          │
│  - Valida serializer                        │
│  - Crea MarketingCampaign en BD              │
└────────┬─────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│  Admin pulsa "Enviar Campaña"               │
│  POST /api/v1/marketing/campaigns/{uuid}/dispatch/
└────────┬─────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│  MarketingCommands.dispatch()               │
│  (202 Accepted - returns immediately)       │
│                                             │
│  1. Para cada channel en campaign.channels: │
│     - GET_OR_CREATE CampaignLog             │
│     - Si ya sent, saltar (idempotencia)     │
│     - ENQUEUE send_via_channel_task         │
│                                             │
└────────┬─────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│  Response: 202 Accepted                     │
│  {                                          │
│    "uuid": "campaign-uuid",                 │
│    "status": "dispatching",                 │
│    "channels": ["email", "whatsapp"]        │
│  }                                          │
└────────────────────────────────────────────┘
         │
         │ (Async via Celery)
         ▼
┌────────────────────────────────────────────┐
│  send_via_channel_task(Celery)              │
│  (max_retries=3, auto-retry on Exception)   │
│                                             │
│  1. Carga CampaignLog                       │
│  2. Si ya sent, return (idempotencia)       │
│  3. Construye CampaignMessage               │
│  4. Obtiene adapter via get_adapter(channel)│
│  5. adapter.send(message)                   │
│  6. Actualiza CampaignLog:                  │
│     - is_sent = success                     │
│     - sent_at = now() si éxito              │
│     - error_message si falla                │
│                                             │
└────────────────────────────────────────────┘
```

### Flujo del Marketing Intelligence Agent

```
┌──────────────────────────────────────────────────┐
│  Trigger: Manual (Admin) o Scheduled (Celery Beat)│
│  POST /api/v1/marketing/agent/run/               │
│  o bien: run_marketing_agent_task.delay()        │
└────────┬─────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│  MarketingAgent.run(triggered_by)                │
│  1. CREATE AgentRun(status='running')            │
└────────┬─────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│  STEP 1: Gather Context (Pull Pattern)           │
│                                                  │
│  MarketingSelector.get_consolidated_dashboard():│
│  ┌────────────────────────────────────────────┐ │
│  │ ShopSummaryProvider.get_summary()          │ │
│  │ - top_products, sales_count, stock_alerts │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │ RentingSummaryProvider.get_summary()       │ │
│  │ - top_equipment, rental_count, stale_items│ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │ ServicesSummaryProvider.get_summary()      │ │
│  │ - top_services, bookings, service_alerts  │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │ Order.objects.aggregate(sales, conversions)  │
│  │ - total_revenue, paid_orders, conv_rate   │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
└────────┬─────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│  STEP 2: Construct Prompts                       │
│                                                  │
│  MARKETING_AGENT_SYSTEM_PROMPT:                 │
│  "You are a marketing expert. Analyze the       │
│   business data and decide whether to dispatch  │
│   a campaign. Return JSON with decision..."      │
│                                                  │
│  ANALYSIS_PROMPT_TEMPLATE:                      │
│  "Current time: {current_time}                  │
│   Shop summary: {shop_summary}                  │
│   Renting summary: {renting_summary}            │
│   Services summary: {services_summary}          │
│   Platform overview: {platform_overview}        │
│   Should we dispatch a campaign? Why?"          │
│                                                  │
└────────┬─────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│  STEP 3: Call LLM via LLMRouter                  │
│                                                  │
│  LLMRouter.complete(system_prompt, user_prompt) │
│                                                  │
│  ┌─────────────────────────────────────────┐   │
│  │ if provider == 'openai':                │   │
│  │   client = OpenAI(api_key=...)          │   │
│  │   response = client.chat.completions... │   │
│  │   return response.choices[0].message... │   │
│  └─────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────┐   │
│  │ elif provider == 'anthropic':           │   │
│  │   client = anthropic.Anthropic(...)     │   │
│  │   response = client.messages.create(... │   │
│  │   return response.content[0].text       │   │
│  └─────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────┐   │
│  │ elif provider == 'gemini':              │   │
│  │   genai.configure(api_key=...)          │   │
│  │   model = genai.GenerativeModel(...)    │   │
│  │   response = model.generate_content(... │   │
│  │   return response.text                  │   │
│  └─────────────────────────────────────────┘   │
│                                                  │
│  Example LLM Response (JSON):                   │
│  {                                              │
│    "should_dispatch": true,                     │
│    "rationale": "Stock of popular items...",   │
│    "campaign_title": "Flash Sale: Tech Items", │
│    "content": "Limited time offer...",          │
│    "channels": ["email", "whatsapp", "ig"],    │
│    "target_audience": "High-value customers"   │
│  }                                              │
│                                                  │
└────────┬─────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│  STEP 4: Parse LLM Decision                      │
│                                                  │
│  decision = json.loads(raw_response)            │
│  UPDATE AgentRun(llm_decision=decision,         │
│                  llm_provider=provider)         │
│                                                  │
│  if not decision.get("should_dispatch"):        │
│    UPDATE AgentRun(status='completed_no_action')│
│    RETURN                                        │
│                                                  │
└────────┬─────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│  STEP 5: Create & Dispatch Campaign               │
│                                                  │
│  CREATE MarketingCampaign(                       │
│    title=decision["campaign_title"],             │
│    content=decision["content"],                  │
│    channels=decision["channels"],                │
│    scheduled_at=now(),                           │
│    target_audience={...}                         │
│  )                                               │
│                                                  │
│  MarketingCommands.dispatch(                     │
│    campaign=campaign,                            │
│    recipient="broadcast"                         │
│  )                                               │
│  → Enqueues send_via_channel_task for each channel
│                                                  │
│  UPDATE AgentRun(                                │
│    status='completed_dispatched',                │
│    campaign=campaign                             │
│  )                                               │
│                                                  │
│  RETURN AgentRun                                 │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Patrón de Adaptadores de Canales

```
AbstractChannelAdapter (Abstract Contract)
│
├─ send(message: CampaignMessage) → dict
│  └─ Returns: {"success": bool, "channel": str, "response": str}
│
├─ EmailChannelAdapter
│   └─ Uses Django Email Backend (SendGrid via django-anymail)
│
├─ WhatsAppChannelAdapter
│   └─ Uses Meta WhatsApp Business API
│
├─ FacebookChannelAdapter
│   └─ Uses Meta Graph API (Page Posts)
│
├─ InstagramChannelAdapter
│   └─ Uses Meta Graph API (Feed Posts)
│
├─ YouTubeChannelAdapter
│   └─ Uses YouTube Data API (Community Tab / Descriptions)
│
├─ TikTokChannelAdapter
│   └─ Uses TikTok Content Posting API v2
│
├─ XChannelAdapter (Twitter)
│   └─ Uses X API v2 (Tweet Creation)
│
└─ GoogleBusinessChannelAdapter
    └─ Uses Google Business Profile API (Posts / Reviews)

Registry Pattern:
get_adapter("email") → EmailChannelAdapter()
get_adapter("whatsapp") → WhatsAppChannelAdapter()
...
```

---

## 📄 Descripción Detallada de Archivos

### `models.py` — Modelos de Dominio

#### **FlashOffer (Ofertas Relámpago)**

```python
class FlashOffer(SintelBaseModel):
    """Ofertas relámpago con tiempo limitado."""
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    # Polymorphic targeting
    variant = ForeignKey(ProductVariant, null=True, blank=True)
    service_variant = ForeignKey(ServiceVariant, null=True, blank=True)
    equipment_variant = ForeignKey(EquipmentVariant, null=True, blank=True)
    
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
```

**Responsabilidades:**
- Define ofertas con tiempo límite (flash sale concept)
- Puede aplicar a productos, servicios, o equipos
- `start_time` / `end_time`: Control de vigencia
- `is_active`: Desactivación manual

#### **PersonalOffer (Ofertas Personalizadas)**

```python
class PersonalOffer(SintelBaseModel):
    """Ofertas personalizadas basadas en historial del usuario."""
    user = ForeignKey(AUTH_USER_MODEL)
    name = models.CharField(max_length=255)
    
    variant = ForeignKey(ProductVariant, null=True, blank=True)
    service_variant = ForeignKey(ServiceVariant, null=True, blank=True)
    equipment_variant = ForeignKey(EquipmentVariant, null=True, blank=True)
    
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.CharField(max_length=255)  # e.g., "Customer repeat", "Interest in tech"
    
    expires_at = models.DateTimeField()
    is_redeemed = models.BooleanField(default=False)
```

**Responsabilidades:**
- Ofertas individualizadas por usuario
- Trazabilidad del motivo (`reason`)
- Control de redención (`is_redeemed`)

#### **MarketingCampaign (Campañas Multicanal)**

```python
class MarketingCampaign(SintelBaseModel):
    title = models.CharField(max_length=255)
    content = models.TextField()
    channels = models.JSONField(default=list)  # e.g., ["email", "whatsapp", "instagram"]
    scheduled_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    target_audience = models.JSONField(default=dict)  # e.g., {"spent_more_than": 1000}
    is_completed = models.BooleanField(default=False)
```

**Responsabilidades:**
- Registro maestro de campañas
- Almacena canales seleccionados como JSONField
- `target_audience`: Filtros para segmentación

#### **CampaignLog (Audit Trail)**

```python
class CampaignLog(SintelBaseModel):
    """
    Audit trail for each campaign dispatch attempt per channel.
    Used for idempotency: if is_sent=True, the worker skips re-sending.
    """
    campaign = ForeignKey(MarketingCampaign, related_name='logs')
    channel = models.CharField(max_length=20)
    recipient = models.CharField(max_length=255)
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('campaign', 'channel', 'recipient')
```

**Responsabilidades:**
- Registra cada intento de envío de campaña
- `unique_together`: Previene duplicados
- `is_sent`: Garantiza idempotencia
- `error_message`: Traza de fallos

#### **AgentRun (Auditoría del Agent)**

```python
class AgentRun(SintelBaseModel):
    STATUS_CHOICES = [
        ('running', 'Ejecutando'),
        ('completed_no_action', 'Completado — Sin acción'),
        ('completed_dispatched', 'Completado — Campaña despachada'),
        ('failed', 'Fallido'),
    ]
    
    triggered_by = models.CharField(max_length=20)  # 'manual' | 'scheduled'
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    llm_provider = models.CharField(max_length=30, blank=True)
    llm_decision = models.JSONField(null=True, blank=True)
    campaign = ForeignKey(MarketingCampaign, null=True, blank=True, related_name='agent_runs')
    notes = models.TextField(blank=True, null=True)
```

**Responsabilidades:**
- Auditoría completa de cada ejecución del agent
- Almacena decisión JSON del LLM
- Trazabilidad de trigger (manual vs scheduled)
- Vinculación con campaña creada

#### **SalesAnalysis (Caché de Analytics)**

```python
class SalesAnalysis(SintelBaseModel):
    """Caché de analítica para Dashboard. Refleja metadata de las apps."""
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    total_sales_amount = models.DecimalField(max_digits=12, decimal_places=2)
    top_product = ForeignKey(ProductVariant, null=True, blank=True)
    top_service = ForeignKey(ServiceVariant, null=True, blank=True)
    top_equipment = ForeignKey(EquipmentVariant, null=True, blank=True)
    
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2)
    
    shop_snapshot = models.JSONField(default=dict)
    renting_snapshot = models.JSONField(default=dict)
    services_snapshot = models.JSONField(default=dict)
```

**Responsabilidades:**
- Caché pre-calculada de analytics
- Snapshots por período para análisis histórico

---

### `api/views.py` — API REST Endpoints

#### **MarketingCampaignViewSet**

```python
class MarketingCampaignViewSet(viewsets.ModelViewSet):
    queryset = MarketingSelector.list_campaigns_for_admin()
    serializer_class = MarketingCampaignSerializer
    lookup_field = 'uuid'
```

**Tipo:** ModelViewSet (CRUD completo)

**Acciones (heredadas de ModelViewSet):**
1. **list()** - GET `/api/v1/marketing/campaigns/`
2. **create()** - POST `/api/v1/marketing/campaigns/`
3. **retrieve()** - GET `/api/v1/marketing/campaigns/{uuid}/`
4. **update()** - PUT `/api/v1/marketing/campaigns/{uuid}/`
5. **partial_update()** - PATCH `/api/v1/marketing/campaigns/{uuid}/`
6. **destroy()** - DELETE `/api/v1/marketing/campaigns/{uuid}/`

#### **FlashOfferViewSet**

```python
class FlashOfferViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MarketingSelector.list_flash_offers()
    serializer_class = FlashOfferSerializer
    lookup_field = 'uuid'
```

**Tipo:** ReadOnlyModelViewSet (solo GET)

**Acciones:**
1. **list()** - GET `/api/v1/marketing/offers/`
2. **retrieve()** - GET `/api/v1/marketing/offers/{uuid}/`

#### **AgentRunViewSet**

```python
class AgentRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MarketingSelector.list_agent_runs()
    serializer_class = AgentRunSerializer
    lookup_field = 'uuid'
```

**Tipo:** ReadOnlyModelViewSet (solo lectura)

**Propósito:** Auditoría de ejecuciones del agent

#### **DashboardViewSet**

```python
class DashboardViewSet(viewsets.ViewSet):
    """Consolidated Intelligence Dashboard for Marketing."""
    
    @extend_schema(responses={200: ConsolidatedDashboardSerializer})
    def list(self, request):
        data = MarketingSelector.get_consolidated_dashboard()
        serializer = ConsolidatedDashboardSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
```

**Tipo:** ViewSet personalizado (no heredado de ModelViewSet)

**Acción:**
- GET `/api/v1/marketing/dashboard/` → Dashboard consolidado

---

### `api/serializers.py` — Serializadores

#### **CampaignLogSerializer**

```python
class CampaignLogSerializer(serializers.ModelSerializer):
    fields = ['uuid', 'channel', 'recipient', 'is_sent', 'sent_at', 'error_message']
```

#### **MarketingCampaignSerializer**

```python
class MarketingCampaignSerializer(serializers.ModelSerializer):
    logs = CampaignLogSerializer(many=True, read_only=True)  # Nested
    
    fields = [
        'id', 'uuid', 'title', 'content', 'channels', 
        'scheduled_at', 'sent_at', 'is_completed', 'logs', 'created_at'
    ]
```

**Nota:** Incluye logs anidados para auditoria en respuestas

#### **FlashOfferSerializer**

```python
class FlashOfferSerializer(serializers.ModelSerializer):
    fields = [
        'id', 'uuid', 'name', 'description', 'discount_percentage',
        'start_time', 'end_time', 'is_active', 'created_at'
    ]
```

#### **AgentRunSerializer**

```python
class AgentRunSerializer(serializers.ModelSerializer):
    fields = [
        'id', 'uuid', 'triggered_by', 'status', 'llm_provider', 
        'llm_decision', 'campaign', 'created_at'
    ]
```

#### **ConsolidatedDashboardSerializer**

```python
class ConsolidatedDashboardSerializer(serializers.Serializer):
    platform_overview = serializers.DictField()
    shop = serializers.DictField()
    renting = serializers.DictField()
    technical_services = serializers.DictField()
```

**Propósito:** Validación de estructura del dashboard consolidado

---

### `services/commands.py` — Operaciones de Escritura

#### **MarketingCommands**

#### **dispatch(campaign, recipient, media_url)**

```python
@staticmethod
def dispatch(campaign: MarketingCampaign, recipient: str, media_url: str = None):
    """
    Enqueues async tasks for each selected channel.
    Called from the API view; returns immediately (202 pattern).
    """
    from marketing.tasks import send_via_channel_task
    
    for channel in campaign.channels:
        log, created = CampaignLog.objects.get_or_create(
            campaign=campaign,
            channel=channel,
            recipient=recipient,
        )
        if log.is_sent:
            continue  # Idempotency: skip already-sent logs
        
        send_via_channel_task.delay(
            campaign_id=str(campaign.uuid),
            channel=channel,
            recipient=recipient,
            media_url=media_url,
            log_id=str(log.uuid),
        )
```

**Responsabilidades:**
1. Itera sobre cada canal en campaign.channels
2. GET_OR_CREATE CampaignLog (previene duplicados)
3. Si ya enviado, salta (idempotencia)
4. ENQUEUE tarea Celery (`send_via_channel_task.delay()`)
5. Retorna inmediatamente (202 pattern)

**Idempotencia:** Si una tarea Celery reintenta y el log ya existe, se salta

#### **send_now(log_id)**

```python
@staticmethod
def send_now(log_id: str):
    """
    Executes a single CampaignLog send. Called by Celery worker.
    """
    log = CampaignLog.objects.select_related('campaign').get(uuid=log_id)
    if log.is_sent:
        return  # Already sent, skip
    
    campaign = log.campaign
    message = CampaignMessage(
        recipient=log.recipient,
        subject=campaign.title,
        body=campaign.content,
    )
    
    adapter = get_adapter(log.channel)  # Get channel adapter
    result = adapter.send(message)
    
    log.is_sent = result["success"]
    log.sent_at = timezone.now() if result["success"] else None
    log.error_message = result["response"] if not result["success"] else ""
    log.save()
```

**Responsabilidades:**
1. Carga CampaignLog
2. Si ya enviado, retorna (doble-check idempotencia)
3. Construye CampaignMessage unificado
4. Obtiene adapter apropiado por canal
5. Invoca adapter.send()
6. Actualiza log con resultado

---

### `services/selectors.py` — Operaciones de Lectura (Read-Only)

#### **MarketingSelector**

#### **list_campaigns_for_admin()**

```python
@staticmethod
def list_campaigns_for_admin() -> QuerySet:
    return MarketingCampaign.objects.all().order_by('-created_at')
```

#### **get_consolidated_dashboard()**

```python
@staticmethod
def get_consolidated_dashboard() -> dict:
    """
    Consolidates statistics from all business apps.
    Uses Pull Pattern: Each app exposes SummaryProvider.
    """
    total_revenue = (
        Order.objects.filter(status='paid')
        .aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    )
    total_orders = Order.objects.count()
    paid_orders = Order.objects.filter(status='paid').count()
    conversion_rate = round((paid_orders / total_orders) * 100, 2) if total_orders > 0 else 0
    
    return {
        'platform_overview': {
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'paid_orders': paid_orders,
            'conversion_rate_pct': conversion_rate,
        },
        'shop': ShopSummaryProvider.get_summary(),
        'renting': RentingSummaryProvider.get_summary(),
        'technical_services': ServicesSummaryProvider.get_summary(),
    }
```

**Patrón Pull:**
- No importa modelos de shop, renting, services directamente
- Cada app expone un `SummaryProvider` con método `get_summary()`
- Marketing "tira" datos via providers, sin acoplamiento directo

**Beneficio:** Aislamiento de cambios en otras apps

#### **get_stale_stock_alerts(days)**

```python
@staticmethod
def get_stale_stock_alerts(days: int = 30) -> dict:
    """Aggregates stale stock signals from all apps for campaign triggers."""
    shop_data = ShopSummaryProvider.get_summary()
    renting_data = RentingSummaryProvider.get_summary()
    services_data = ServicesSummaryProvider.get_summary()
    
    return {
        'shop_stale_count': shop_data['stale_stock_count'],
        'shop_stale_ids': shop_data['stale_stock_record_ids'],
        'renting_stale_count': renting_data['stale_equipment_count'],
        'renting_stale_ids': renting_data['stale_equipment_record_ids'],
        'services_stale_count': services_data['stale_services_count'],
        'services_stale_ids': services_data['stale_service_record_ids'],
    }
```

**Propósito:** Agregar alertas de stock obsoleto para disparar campañas de liquidación

#### **get_user_marketing_profile(user)**

```python
@staticmethod
def get_user_marketing_profile(user) -> dict:
    """Analiza el historial completo de un usuario para personalización."""
    orders = Order.objects.filter(user=user, status='paid')
    total_spent = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    product_count = OrderItem.objects.filter(order__user=user, variant__isnull=False).count()
    service_count = OrderItem.objects.filter(order__user=user, service_variant__isnull=False).count()
    rental_count = OrderItem.objects.filter(order__user=user, equipment_variant__isnull=False).count()
    
    preference = max(
        [('products', product_count), ('services', service_count), ('renting', rental_count)],
        key=lambda x: x[1]
    )[0]
    
    return {
        'user_uuid': str(user.uuid),
        'total_spent': total_spent,
        'orders_count': orders.count(),
        'preference': preference,
        'product_purchases': product_count,
        'service_purchases': service_count,
        'rental_purchases': rental_count,
    }
```

**Propósito:** Perfil completo para personalización de ofertas

#### **get_campaign_targets_for_stale_products()**

```python
@staticmethod
def get_campaign_targets_for_stale_products() -> list:
    """Returns users who have shown interest in stale product categories."""
    stale_data = MarketingSelector.get_stale_stock_alerts()
    stale_shop_ids = stale_data['shop_stale_ids']
    
    targeted_users = (
        OrderItem.objects.filter(
            order__status='paid',
            variant__isnull=False
        ).values('order__user__email', 'order__user__uuid')
        .distinct()
    )
    return list(targeted_users[:50])
```

**Propósito:** Segmentación para campañas de liquidación

---

### `channels/base.py` — Contrato de Adaptadores

```python
@dataclass
class CampaignMessage:
    """Unified message structure for all channels."""
    recipient: str          # email, phone, page_id, etc.
    subject: str            # Email subject / social post title
    body: str               # Main content
    media_url: Optional[str] = None

class AbstractChannelAdapter(ABC):
    """Adapter interface for all marketing channels."""
    channel_name: str = "base"
    
    @abstractmethod
    def send(self, message: CampaignMessage) -> dict:
        """
        Send a message through the channel.
        Returns: dict with keys: success (bool), channel, response (str)
        """
        raise NotImplementedError
```

**Propósito:**
- Define contrato que todos los adapters deben implementar
- `CampaignMessage`: Estructura unificada independiente del canal
- Cada adapter implementa `send()` de forma específica

**[2026-07-12] Credenciales via `organization`, no `settings` directo:** los 8 adapters ya no
leen `settings.META_ACCESS_TOKEN`/`settings.DEFAULT_FROM_EMAIL`/etc directamente. Usan
`organization.services.selectors.OrganizationSelector.get_integration_settings()` (dict
fachada de solo lectura, las credenciales SIGUEN en `.env` — decision de seguridad, ver
`organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md`) para
Facebook/Instagram/YouTube/TikTok/X/WhatsApp/Google Business, y `get_email_settings()` para
`EmailChannelAdapter`. Al agregar un canal nuevo, seguir este mismo patron — nunca volver a
`settings.X` directo para credenciales de integracion.

---

### `channels/registry.py` — Registro de Canales

```python
CHANNEL_REGISTRY = {
    "email": EmailChannelAdapter,
    "whatsapp": WhatsAppChannelAdapter,
    "facebook": FacebookChannelAdapter,
    "instagram": InstagramChannelAdapter,
    "youtube": YouTubeChannelAdapter,
    "tiktok": TikTokChannelAdapter,
    "x": XChannelAdapter,
    "google_business": GoogleBusinessChannelAdapter,
}

def get_adapter(channel_name: str):
    """Returns an instantiated adapter for the given channel name."""
    adapter_class = CHANNEL_REGISTRY.get(channel_name)
    if not adapter_class:
        raise ValueError(f"Canal desconocido: '{channel_name}'...")
    return adapter_class()
```

**Propósito:**
- Mapeo centralizado de canales a adapters
- Factory function para obtener adapter por nombre
- Extensible: agregar nuevo canal = agregar entrada en registry

---

### `channels/email_channel.py` — Ejemplo de Adapter

```python
class EmailChannelAdapter(AbstractChannelAdapter):
    channel_name = "email"
    
    def send(self, message: CampaignMessage) -> dict:
        try:
            email = EmailMultiAlternatives(
                subject=message.subject,
                body=message.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[message.recipient],
            )
            email.send(fail_silently=False)
            return {"success": True, "channel": self.channel_name, "response": "Sent"}
        except Exception as e:
            return {"success": False, "channel": self.channel_name, "response": str(e)}
```

**Responsabilidades:**
1. Hereda de AbstractChannelAdapter
2. Implementa send(message) específicamente para email
3. Usa Django Email Backend (compatible SendGrid via django-anymail)
4. Retorna dict con success/error

**Patrón:** Todos los adapters siguen este mismo esquema

---

### `agent/brain.py` — Marketing Intelligence Agent

```python
class MarketingAgent:
    """The autonomous brain of the marketing module."""
    
    def run(self, triggered_by: str = "manual") -> AgentRun:
        """Execute one analysis cycle."""
        run = AgentRun.objects.create(triggered_by=triggered_by, status="running")
        
        try:
            # 1. Gather context
            dashboard = MarketingSelector.get_consolidated_dashboard()
            user_prompt = ANALYSIS_PROMPT_TEMPLATE.format(...)
            
            # 2. Call LLM
            raw_response = LLMRouter.complete(
                system_prompt=MARKETING_AGENT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            
            # 3. Parse decision
            decision = json.loads(raw_response)
            run.llm_decision = decision
            run.llm_provider = self._get_provider()
            
            if not decision.get("should_dispatch", False):
                run.status = "completed_no_action"
                run.notes = decision.get("rationale", "No action needed.")
                run.save()
                return run
            
            # 4. Create campaign
            campaign = MarketingCampaign.objects.create(
                title=decision["campaign_title"],
                content=decision["content"],
                channels=decision.get("channels", []),
                scheduled_at=timezone.now(),
                target_audience={"description": decision.get("target_audience", "")},
            )
            
            # 5. Dispatch
            MarketingCommands.dispatch(campaign=campaign, recipient="broadcast")
            
            run.status = "completed_dispatched"
            run.campaign = campaign
            run.save()
            
            return run
            
        except Exception as e:
            run.status = "failed"
            run.notes = str(e)
            run.save()
            return run
```

**Responsabilidades (Orquestación):**
1. Recopila datos de contexto (pull pattern)
2. Construye prompts para LLM
3. Llama a LLMRouter (abstracción de proveedor)
4. Parsea respuesta JSON
5. Crea MarketingCampaign si warranted
6. Dispara campña via MarketingCommands
7. Registra ejecución en AgentRun

---

### `agent/llm_router.py` — Enrutador de Proveedores LLM

```python
class LLMRouter:
    @staticmethod
    def complete(system_prompt: str, user_prompt: str) -> str:
        """Send prompts to the configured LLM."""
        provider = getattr(settings, 'MARKETING_AGENT_PROVIDER', 'openai').lower()
        
        if provider == 'openai':
            return LLMRouter._call_openai(system_prompt, user_prompt)
        elif provider == 'anthropic':
            return LLMRouter._call_anthropic(system_prompt, user_prompt)
        elif provider == 'gemini':
            return LLMRouter._call_gemini(system_prompt, user_prompt)
```

**Soporta 3 proveedores:**
1. **OpenAI** (GPT-4o): `OPENAI_API_KEY`, `OPENAI_MODEL`
2. **Anthropic** (Claude): `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
3. **Google Gemini**: `GEMINI_API_KEY`, `GEMINI_MODEL`

**Cada proveedor:**
- Usa la configuración de settings
- Retorna respuesta JSON parseable
- Maneja errors automáticamente

---

### `tasks.py` — Tareas Celery

#### **run_marketing_agent_task()**

```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    name="marketing.run_agent",
    queue="marketing",
)
def run_marketing_agent_task(self, triggered_by: str = "scheduled"):
    """
    Triggers a full MarketingAgent analysis cycle.
    Can be triggered manually via API or scheduled via Celery Beat.
    """
    from marketing.agent.brain import MarketingAgent
    agent = MarketingAgent()
    run = agent.run(triggered_by=triggered_by)
    return {"status": run.status, "run_uuid": str(run.uuid)}
```

**Propósito:**
- Ejecutar agent análisis completo
- Auto-retry: 2 reintentos si falla
- Puede ser manual (from API) o scheduled (Celery Beat)

#### **send_via_channel_task()**

```python
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=60,
    name="marketing.send_via_channel",
    queue="marketing",
)
def send_via_channel_task(self, campaign_id: str, channel: str, recipient: str,
                          media_url: str = None, log_id: str = None):
    """
    Sends a single campaign message through one channel adapter.
    Called by MarketingCommands.dispatch() — one task per channel per recipient.
    Idempotency enforced via CampaignLog.is_sent.
    """
    from marketing.services.commands import MarketingCommands
    MarketingCommands.send_now(log_id=log_id)
```

**Propósito:**
- Enviar mensaje por UN canal específico
- Auto-retry: 3 reintentos con delay de 60s
- Llamado por dispatch() para cada canal
- Idempotencia garantizada en send_now()

---

## 🔄 Flujos de Casos de Uso

### Caso 1: Crear y Despachar Campaña Manualmente

```
Admin: POST /api/v1/marketing/campaigns/
{
    "title": "Summer Clearance",
    "content": "30% off selected items!",
    "channels": ["email", "whatsapp", "instagram"],
    "scheduled_at": "2026-05-14T15:00:00Z",
    "target_audience": {"purchased_before": true}
}

→ MarketingCampaignViewSet.create()
→ MarketingCampaignSerializer.create()
→ MarketingCampaign.objects.create()
→ Response: 201 Created {uuid, ...}

Admin: POST /api/v1/marketing/campaigns/{uuid}/dispatch/
{
    "recipient": "user@example.com",
    "media_url": "https://..."
}

→ MarketingCommands.dispatch(campaign, "user@example.com")
→ Para cada canal en ["email", "whatsapp", "instagram"]:
     - CampaignLog.get_or_create(campaign, channel, recipient)
     - send_via_channel_task.delay(...)  [Celery]
→ Response: 202 Accepted {status: "dispatching"}

[Async via Celery Worker]
→ send_via_channel_task()
→ MarketingCommands.send_now(log_id)
→ adapter = get_adapter("email")
→ adapter.send(message)
→ CampaignLog.update(is_sent=True, sent_at=now)
```

### Caso 2: Marketing Agent Análisis Automático

```
Trigger: POST /api/v1/marketing/agent/run/
o
Scheduled: Celery Beat (cada hora, ej)

→ run_marketing_agent_task()
→ MarketingAgent.run(triggered_by="manual" o "scheduled")

1. Gather Context:
   - ShopSummaryProvider.get_summary()
   - RentingSummaryProvider.get_summary()
   - ServicesSummaryProvider.get_summary()
   - Order.aggregate(sales, conversions)

2. Build Prompts:
   SYSTEM: "You are a marketing expert. Analyze business data and decide..."
   USER: "Current time: {now}. Shop: {data}. Renting: {data}. Services: {data}..."

3. Call LLM:
   LLMRouter.complete(system, user)
   → OpenAI GPT-4o / Anthropic Claude / Google Gemini
   
4. Example LLM Response:
   {
      "should_dispatch": true,
      "campaign_title": "Tech Tuesday Flash Sale",
      "content": "GPU prices slashed for 24h...",
      "channels": ["email", "instagram", "facebook"],
      "target_audience": "Tech enthusiasts",
      "rationale": "High interest in electronics..."
   }

5. Parse & Create Campaign:
   MarketingCampaign.create(title, content, channels, ...)

6. Dispatch:
   MarketingCommands.dispatch(campaign, recipient="broadcast")

7. Record Result:
   AgentRun.update(status="completed_dispatched", campaign=..., llm_decision=...)
   
Response: AgentRun {uuid, status, llm_provider, campaign_uuid, ...}
```

### Caso 3: Consultar Dashboard Consolidado

```
Frontend: GET /api/v1/marketing/dashboard/

→ DashboardViewSet.list()
→ MarketingSelector.get_consolidated_dashboard()

1. Query Orders:
   - total_revenue = Sum(Order.total_amount where status='paid')
   - total_orders = Count(Order)
   - paid_orders = Count(Order where status='paid')
   - conversion_rate = (paid_orders / total_orders) * 100

2. Pull from SummaryProviders:
   - shop_data = ShopSummaryProvider.get_summary()
   - renting_data = RentingSummaryProvider.get_summary()
   - services_data = ServicesSummaryProvider.get_summary()

3. Aggregate:
   return {
       "platform_overview": {
           "total_revenue": 125000.00,
           "total_orders": 450,
           "paid_orders": 425,
           "conversion_rate_pct": 94.44
       },
       "shop": {
           "total_products": 1250,
           "top_product": "Laptop X1",
           "stale_stock_count": 23,
           ...
       },
       "renting": {...},
       "technical_services": {...}
   }

→ ConsolidatedDashboardSerializer validates structure
→ Response: 200 OK {platform_overview, shop, renting, technical_services}
```

---

## 🏗️ Patrones de Diseño Utilizados

### 1. **Service Layer Pattern**
- **Commands**: Escritura / dispatch (dispatch(), send_now())
- **Selectors**: Lectura (get_consolidated_dashboard(), get_user_marketing_profile())

### 2. **Channel Adapter Pattern** (Strategy Pattern)
```
AbstractChannelAdapter ← Contract
    ↑
    ├─ EmailChannelAdapter (Django Email)
    ├─ WhatsAppChannelAdapter (Meta API)
    ├─ FacebookChannelAdapter (Meta Graph)
    ├─ InstagramChannelAdapter (Meta Graph)
    ├─ YouTubeChannelAdapter (YouTube API)
    ├─ TikTokChannelAdapter (TikTok API)
    ├─ XChannelAdapter (X API v2)
    └─ GoogleBusinessChannelAdapter (Google My Business)
    
get_adapter(channel_name) → adapter_instance
adapter.send(message) → {"success": bool, ...}
```

### 3. **Registry Pattern**
- Mapeo centralizado de canales a implementaciones
- Factory function para obtener adapters
- Extensible sin modificar código existente

### 4. **Pull-based Data Integration**
```
MarketingSelector.get_consolidated_dashboard()
    ↓
ShopSummaryProvider.get_summary()      (shop app)
RentingSummaryProvider.get_summary()   (renting app)
ServicesSummaryProvider.get_summary()  (technical_services app)
    ↓
Marketing "tira" datos, no push
Desacoplamiento: cambios en otras apps no afectan marketing
```

### 5. **Async Dispatch with Idempotence**
```
MarketingCommands.dispatch() → 202 Accepted (immediate)
    ↓
send_via_channel_task.delay() [Celery Queue]
    ↓
get_or_create(CampaignLog) → previene duplicados
    ↓
if log.is_sent: return (idempotencia)
    ↓
adapter.send(message)
    ↓
log.update(is_sent=True/False, error_message)
```

### 6. **LLM Provider Abstraction**
```
LLMRouter.complete(system_prompt, user_prompt)
    ↓
if provider == 'openai': return _call_openai(...)
if provider == 'anthropic': return _call_anthropic(...)
if provider == 'gemini': return _call_gemini(...)

Settings: MARKETING_AGENT_PROVIDER = 'openai' | 'anthropic' | 'gemini'
```

### 7. **Immutable Audit Trail**
```
CampaignLog: unique_together(campaign, channel, recipient)
    - is_sent: boolean idempotency marker
    - sent_at: timestamp de envío exitoso
    - error_message: trazabilidad de fallos
    
AgentRun: Registro completo de cada ejecución
    - llm_decision: JSON de decisión del LLM
    - campaign: FK a campaña creada (si aplica)
    - status: running → completed_* / failed
    - notes: trazabilidad
```

---

## ⚡ Consideraciones de Rendimiento

### 1. **Async Dispatch Pattern**
```python
dispatch() → 202 Accepted (fast return to client)
    ↓
send_via_channel_task.delay() [enqueued immediately]
    ↓
Celery Worker: dequeues cuando disponible
    ↓
adapter.send() - blocking I/O a external services
```

**Beneficio:** No bloquea API, escalable a miles de campañas

### 2. **Idempotency via CampaignLog.is_sent**
```python
if log.is_sent:
    return  # Skip, already processed

# Even if Celery retries due to network error:
# 2nd invocation of send_via_channel_task finds log.is_sent=True
# No double-sending
```

**Beneficio:** Safe retries, guaranteed exactly-once delivery

### 3. **Pull Pattern en Lugar de Push**
```
PROBLEMA (Push):
Marketing importa directamente de shop, renting, services
    ↓
Cada cambio en shop puede romper marketing

SOLUCIÓN (Pull):
shop.SummaryProvider.get_summary() ← shop expone interface
renting.SummaryProvider.get_summary() ← renting expone interface
services.SummaryProvider.get_summary() ← services expone interface
    ↓
Marketing "tira" datos via interfaces estables
```

**Beneficio:** Desacoplamiento, cambios internos no se propagan

### 4. **LLM Caching de Respuestas** (Opportunity)
```python
# Could add:
cache_key = f"agent_decision:{provider}:{hash(dashboard_data)}"
cached = cache.get(cache_key)
if cached:
    return cached

raw_response = LLMRouter.complete(...)
cache.set(cache_key, raw_response, timeout=3600)
```

**Beneficio:** Reduce API calls a LLM si contexto idéntico

### 5. **Selective Retries en Celery**
```python
@shared_task(
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(NetworkError, TimeoutError),  # Specific errors
)
def send_via_channel_task(...):
    ...
```

**Beneficio:** Solo reintentar en fallos transitorios (network), no en validation errors

---

## 🔐 Validaciones y Seguridad

### 1. **Validation en Serializers**
```python
class MarketingCampaignSerializer:
    # DRF auto-validates:
    # - channels: lista válida
    # - scheduled_at: datetime válido
    # - target_audience: JSON válido
```

### 2. **Unique Constraint en CampaignLog**
```python
class Meta:
    unique_together = ('campaign', 'channel', 'recipient')
```

**Propósito:** Prevenir duplicados, garantiza idempotencia

### 3. **API Permissions** (Not shown in code, presumed)
```python
# Presumed in settings:
REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
    'rest_framework.permissions.IsAuthenticated',
]
```

**Propósito:** Solo usuarios autenticados pueden crear campañas

### 4. **LLM Prompt Injection Protection** (Opportunity)
```python
# Current: Construye prompt con datos de BD
user_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
    platform_overview=json.dumps(dashboard, default=str),
    ...
)

# Risk: Si target_audience contiene prompt injection
# Solution: Sanitize target_audience antes de template
```

---

## 🚀 Mejoras Futuras / Roadmap

### 1. **A/B Testing de Campañas**
```python
class CampaignVariant(SintelBaseModel):
    campaign = ForeignKey(MarketingCampaign)
    variant_name = CharField()  # "A", "B", "Control"
    content = TextField()
    
class CampaignMetric(SintelBaseModel):
    variant = ForeignKey(CampaignVariant)
    metric_type = CharField()  # "open_rate", "click_rate", "conversion"
    value = DecimalField()
```

### 2. **Scheduling Automático con Celery Beat**
```python
# Schedule in settings:
CELERY_BEAT_SCHEDULE = {
    'run-marketing-agent-hourly': {
        'task': 'marketing.run_agent',
        'schedule': crontab(minute=0),  # Every hour
    },
}
```

### 3. **Webhooks para Eventos Externos**
```python
# When Campaign sent successfully:
send_campaign_notification_webhook(campaign, channel, recipient)
    ↓
POST https://client-webhook-url/campaign-sent
{
    "campaign_uuid": "...",
    "channel": "email",
    "recipient": "user@example.com",
    "sent_at": "2026-05-14T15:30:00Z"
}
```

### 4. **Advanced Segmentation Engine**
```python
class AudienceSegment(SintelBaseModel):
    name = CharField()  # "High-Value Customers"
    filters = JSONField()  # {
                            #    "min_total_spent": 5000,
                            #    "last_purchase_days": 90,
                            #    "categories": ["electronics"]
                            # }
```

### 5. **Campaign Analytics Dashboard**
```
Métricas por campaña:
- Delivery rate (sent / enqueued)
- Open rate (email)
- Click rate (links)
- Conversion rate (to purchase)
- Revenue impact (attribution)
```

### 6. **Multi-Language Support en Prompts**
```python
MARKETING_AGENT_SYSTEM_PROMPT_ES = "..."
MARKETING_AGENT_SYSTEM_PROMPT_EN = "..."

# Select based on user.language_preference
```

### 7. **Integration con Predictive Analytics**
```python
# Predict next purchase time for each user
# Recommend best time to send campaign
from ml_models import PredictiveModel
predicted_purchase_time = PredictiveModel.predict_next_purchase(user)
```

---

## 📊 Flujo de Integración con otras Apps (Pull Pattern)

```
SHOP MODULE:
├─ ShopSummaryProvider.get_summary() →
│  {
│    "total_products": 1250,
│    "top_product": "Product X",
│    "stale_stock_count": 23,
│    "stale_stock_record_ids": ["uuid1", "uuid2", ...],
│    "sales_7d": 450,
│    "revenue_7d": 45000.00
│  }

RENTING MODULE:
├─ RentingSummaryProvider.get_summary() →
│  {
│    "total_equipment": 320,
│    "top_equipment": "Equipment Y",
│    "stale_equipment_count": 12,
│    "rentals_7d": 85,
│    "revenue_7d": 8500.00
│  }

TECHNICAL_SERVICES MODULE:
├─ ServicesSummaryProvider.get_summary() →
│  {
│    "total_services": 45,
│    "top_service": "Service Z",
│    "stale_services_count": 5,
│    "bookings_7d": 210,
│    "revenue_7d": 12000.00
│  }

ORDERS MODULE:
├─ Order.objects.aggregate(
│    total_revenue: Sum('total_amount'),
│    total_count: Count('id'),
│    paid_count: Count(...where status='paid')
│  )

MARKETING MODULE:
└─ get_consolidated_dashboard()
    └─ Pulls data from all above
        → Passes to LLM Agent
        → Agent reasons and dispatches campaigns
```

---

## 🔌 `integrations/meta/` — Frontera HTTP hacia Meta (2026-08-31)

FASE 3 del plan de integracion Meta Business
(`Documentacion/Arquitectura_general/META_BUSINESS_INTEGRATION_MASTER_PLAN.md`).

**Regla:** ningun `requests.*` a `graph.facebook.com` fuera de este paquete. Vive
bajo `marketing/` porque marketing es el dominio dueno de Meta/Ads; los demas
consumidores importan el subcliente que necesitan (`notifications/clients/whatsapp.py`
importa `MetaWhatsAppClient`).

| Archivo | Contenido |
|---|---|
| `client.py` | `MetaGraphClient` — transporte puro, equivalente a `payment/online/wompi_client.py::WompiApiClient`. `get/post/delete/paginate` (paginacion por cursores). Version de Graph API, timeout, y clasificacion de errores: HTTP 429 o Graph code `{4,17,32,613,80004,80014}` → `MetaRateLimitError`; 401/403 o code `{102,190,200,...}` → `MetaAuthError`; 5xx / error de red → `MetaApiTransientError`; resto 4xx → `MetaApiError`; falta token/id → `MetaConfigError` (antes de tocar la red). **Cero logica de negocio.** Lee la config via `OrganizationSelector.get_integration_settings()`. |
| `exceptions.py` | Jerarquia. `MetaApiTransientError`/`MetaRateLimitError` son "seguro reintentar"; el resto es definitivo. |
| `signatures.py` | `verify_meta_webhook_signature(app_secret, raw_body, header)` — funcion pura, sin Django, fail-closed si `app_secret` vacio. Reusable por futuros webhooks de Meta. |
| `whatsapp.py` | `MetaWhatsAppClient(send_template, send_text)` sobre `MetaGraphClient`. Reemplazo del transporte propio que vivia en `notifications/clients/whatsapp.py`. |
| `marketing.py` | `MetaMarketingClient` (FASE 7) — **solo GET**: `list_campaigns` / `get_campaign` / `list_adsets` / `list_ads` / `get_insights` (soporta `time_range` o `date_preset`) / `get_account_summary`. `_act()` antepone `act_` al ad account id. |

**Config:** todo via `settings`/`.env` + `OrganizationSelector.get_integration_settings()`
(claves `meta_access_token`, `meta_graph_api_version`, `meta_ad_account_id`, etc.).
Nada en BD. Los tokens nunca llegan al frontend / LLM / logs.

**Adapters de canal** (`channels/facebook_channel.py`, `whatsapp_channel.py`,
`instagram_channel.py`) migrados a `MetaGraphClient` / `MetaWhatsAppClient` (FASE 4,
2026-08-31). Interfaz `AbstractChannelAdapter.send()` intacta.

### `services/meta_selectors.py` + `api/internal_ai.py` (Meta Ads READ, FASE 7+9)

- `MetaCampaignSelector` (`services/meta_selectors.py`) — solo lectura, normaliza
  la salida de `MetaMarketingClient` (presupuestos de unidad minima -> decimal
  string; `purchase_roas` lista -> numero). Propaga las excepciones tipadas de la
  frontera Meta **sin envolver** — cada vista las mapea.
- `AiMetaCampaignsView` / `AiMetaCampaignDetailView` / `AiMetaInsightsView` /
  `AiMetaAccountSummaryView` en `api/internal_ai.py`, registradas en
  `ecommerce/internal_ai_urls.py` bajo `marketing/meta/...`. `IsAdminUser`.
  `_meta_error_response()`: `MetaConfigError` -> 503, resto -> 502. Consumidas por
  el ai_engine via `http_bridge.py`, nunca por el frontend.
- Escrituras (pause/resume/budget/create) NO existen aun — FASE 16-18, detras de
  Policy Layer + aprobacion humana.

---

## 📝 Resumen de la Arquitectura

| Aspecto | Detalles |
|---------|----------|
| **Patrón Principal** | Service Layer + Channel Adapters + LLM Agent |
| **Modelos** | Campaigns, FlashOffers, PersonalOffers, CampaignLog, AgentRun, SalesAnalysis |
| **Operaciones** | Commands para dispatch, Selectors para consolidate & profile |
| **Canales** | Email, WhatsApp, Facebook, Instagram, YouTube, TikTok, X, Google Business |
| **LLM Support** | OpenAI, Anthropic, Google Gemini |
| **Async** | Celery tasks con idempotencia garantizada |
| **Integración** | Pull-based (SummaryProviders) sin acoplamiento directo |
| **Auditoría** | CampaignLog (delivery trail), AgentRun (execution trail) |
| **API** | DRF ViewSets, readonly + CRUD campaigns |

---

## Actualizacion 2026-09-24 (plan Campanas CRUD/Catalogo/Media/Canales)

Nuevos modelos: `CampaignItem`, `CampaignBenefit`, `CampaignMedia`; campos de contenido estructurado y
vigencia en `MarketingCampaign`. Nuevas acciones en `MarketingCampaignViewSet`: media (upload/reorder/
toggle/delete), `send/`, `preview/`. `MarketingCommands.build_message()` unifica preview y envio real;
`dispatch()` acepta `channels`. Eventos `marketing_event=...` en logs. Detalle en
`docs/marketing/MARKETING_CAMPAIGN_MODEL.md`, `MARKETING_CHANNELS.md`, `MARKETING_MEDIA.md`.

**Última actualización:** 2026-09-24

