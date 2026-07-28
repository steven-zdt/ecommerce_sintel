from decimal import Decimal, InvalidOperation


class LaborConditionsEvaluator:
    """
    Deduce automaticamente las condiciones tecnicas de mano de obra a partir
    de la altura de instalacion -- unica pregunta que el cliente responde
    sobre este tema (plan de "Simplificacion Inteligente" 2026-07-23). El
    cliente nunca ve estas reglas ni sus resultados; solo el asesor
    comercial, en el visor de solicitudes (QuotationSerializer.labor_analysis
    -> RequestViewer.vue).

    Los umbrales de RISK_THRESHOLDS son un punto de partida razonable, NO
    una clasificacion oficial unica aplicable a todas las ARL/aseguradoras
    -- deben validarse contra la normativa vigente antes de usarse para
    decisiones de seguridad reales. Se centralizan aqui (en vez de en el
    frontend o repetidos en cada vista) para que un cambio de normativa
    solo requiera editar esta clase.
    """

    WORK_AT_HEIGHT_THRESHOLD = Decimal('2')
    SCAFFOLD_EQUIPMENT_THRESHOLD = Decimal('4')
    NO_RISK_LABEL = 'Sin trabajo en alturas'

    # (altura minima inclusive, etiqueta de nivel) -- evaluado de mayor a menor.
    RISK_THRESHOLDS = (
        (Decimal('6'), 'Nivel 5'),
        (Decimal('5'), 'Nivel 4'),
        (Decimal('4'), 'Nivel 3'),
        (Decimal('3'), 'Nivel 2'),
        (Decimal('2'), 'Nivel 1'),
    )

    @classmethod
    def evaluate(cls, height):
        """height: valor crudo de installation_height (str/int/float/Decimal/None).
        Retorna None si no hay una altura numerica valida."""
        try:
            height = Decimal(str(height))
        except (InvalidOperation, TypeError, ValueError):
            return None

        risk_level = cls.NO_RISK_LABEL
        for threshold, label in cls.RISK_THRESHOLDS:
            if height >= threshold:
                risk_level = label
                break

        return {
            'installation_height': height,
            'work_at_height': height >= cls.WORK_AT_HEIGHT_THRESHOLD,
            'risk_level': risk_level,
            'required_access_equipment': (
                'Andamio' if height >= cls.SCAFFOLD_EQUIPMENT_THRESHOLD else 'Escalera'
            ),
        }
