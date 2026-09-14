from ai_provider.models import AIChannelConfig, AIModel, AIProvider


class AIProviderSelector:
    @staticmethod
    def list_providers(include_inactive: bool = True):
        qs = AIProvider.objects.filter(is_deleted=False)
        if not include_inactive:
            qs = qs.filter(is_active=True)
        return qs.order_by('display_order', 'name')

    @staticmethod
    def get_provider(uuid):
        return AIProvider.objects.get(uuid=uuid, is_deleted=False)

    @staticmethod
    def get_default_provider():
        """Plan 'AI Provider Runtime' FASE 2 -- proveedor marcado is_default=True, o
        None si ninguno lo esta (no hay fallback implicito: un canal sin config
        explicita debe caer a LOCAL_MODEL_CHAIN, no adivinar un proveedor)."""
        return AIProvider.objects.filter(is_deleted=False, is_default=True, is_active=True).first()


class AIModelSelector:
    """Plan 'AI Provider Runtime' FASE 5 -- separado de AIProviderSelector (antes
    'get_model()'/'list_models_for_provider()' vivian mezclados ahi; encontrado como
    gap real en AI_PROVIDER_RUNTIME_AUDIT.md seccion 10)."""

    @staticmethod
    def get(uuid):
        return AIModel.objects.select_related('provider').get(uuid=uuid, is_deleted=False)

    @staticmethod
    def list_for_provider(provider: AIProvider, include_inactive: bool = True):
        qs = provider.models.filter(is_deleted=False)
        if not include_inactive:
            qs = qs.filter(is_active=True)
        return qs.order_by('model_id')

    @staticmethod
    def get_default_for_provider(provider: AIProvider):
        return provider.models.filter(is_deleted=False, is_default=True, is_active=True).first()


class AIChannelConfigSelector:
    @staticmethod
    def get_or_create_config(channel: str = AIChannelConfig.CHANNEL_SUPPORT_CHAT) -> AIChannelConfig:
        config, _ = AIChannelConfig.objects.get_or_create(channel=channel)
        return config

    @staticmethod
    def get_resolved_chain(channel: str = AIChannelConfig.CHANNEL_SUPPORT_CHAT) -> list[AIModel]:
        """[primary, *fallbacks] en orden, saltando proveedores/modelos inactivos o
        borrados -- forma que consume el endpoint interno de AI Engine (FASE 2).

        FASE 19 (plan 'AI Provider Runtime', 2026-08-13): fix de un gap real que el
        propio models.py (AIChannelConfig.enabled, comentario junto al campo) ya
        documentaba desde FASE 4/18 pero nunca quedo cableado -- con enabled=False
        esta funcion devolvia la cadena completa igual, es decir el toggle "IA
        activa/inactiva" del canal no apagaba nada. Ahora enabled=False se trata
        igual que "cadena vacia" (AI Engine cae a LOCAL_MODEL_CHAIN)."""
        config = AIChannelConfigSelector.get_or_create_config(channel)
        chain: list[AIModel] = []
        if not config.enabled:
            return chain
        primary = config.primary_model
        if primary and not primary.is_deleted and primary.is_active and primary.provider.is_active:
            chain.append(primary)
        fallbacks = (
            config.fallbacks.filter(is_deleted=False)
            .select_related('model', 'model__provider')
            .order_by('order')
        )
        for fb in fallbacks:
            model = fb.model
            if not model.is_deleted and model.is_active and model.provider.is_active:
                chain.append(model)
        return chain
