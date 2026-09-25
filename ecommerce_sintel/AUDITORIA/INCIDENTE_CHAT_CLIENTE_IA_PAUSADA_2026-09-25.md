# Incidente: el chat de soporte del cliente no respondia en sintel.net.co/tienda (2026-09-25)

Estado: RESUELTO. Sin cambios de codigo: era estado de datos (una sala con la IA pausada).

## Sintoma
Tras desplegar (~11:45), el admin funcionaba pero el chat del lado cliente en `https://sintel.net.co/tienda` no respondia.

## Diagnostico (por capas, solo lectura)
| Capa | Evidencia | Conclusion |
|---|---|---|
| Despliegue | 10 servicios `sintel_prod_*` healthy; panel y API 200 | ok |
| ADK | log sin ningun `POST /chat` desde el arranque | la peticion no llegaba al ADK |
| Django | `WSCONNECT /ws/support/chat/`, `[WS][AUTH] token valido`, `[CHAT] room=8a29d9f2... status=sent` | el mensaje llegaba a Django |
| Django | **no** aparecia `[CHAT] ... AI request status=started` | `is_ai_mode_active(room)` = False |
| BD (sala) | `status=OPEN`, **`ai_paused=True`**, `assigned_admin=None`; los 8 ultimos mensajes eran todos del cliente, ninguno del bot desde el 24-09 | la IA llevaba pausada desde entonces |
| LM Studio | HTTP 200 en el host | el modelo no era el problema |

## Causa
La sala de prueba (`ceo@sintel.net.co`, que es admin y prueba el lado cliente con su propia cuenta) tenia `ai_paused=True`. Desde F18 (2026-09-24) una respuesta humana en
la sala pausa la IA y **solo una reactivacion explicita** la vuelve a activar. El origen exacto de la pausa no se pudo confirmar (los logs previos se perdieron al recrear
`django`); encaja con una respuesta del admin desde el panel en esa misma sala o con una escalacion. `is_ai_mode_active` devuelve `False` **sin dejar traza en el log**, por
eso parecia un fallo silencioso.

## Solucion
`ChatCommands.resume_ai(room, admin)` (comando oficial de Support, con autorizacion expresa del usuario): `ai_paused=False`, libera `assigned_admin` y deja el mensaje
"El asistente virtual volvio a atender esta conversacion". Verificado: `is_ai_mode_active` paso de False a True; el usuario confirmo que el chat responde.

## Reglas / prevencion
1. Un chat "que no responde" sin errores casi siempre es **la IA inactiva en esa sala**, no una caida: buscar `AI request status=started` tras `status=sent` (playbook G).
2. Probar el chat del cliente con una cuenta **que no sea admin**; si un admin responde desde el panel en su sala de prueba, la IA se pausa.
3. Una sala de cliente real queda sin IA tras una respuesta humana hasta pulsar "Reactivar IA" (`POST /api/v1/support/chats/<uuid>/resume-ai/`): es diseno, no bug.
4. `AI_PAUSE_ON_HUMAN_REPLY=false` desactiva la pausa automatica (no recomendado: la IA y el humano responderian a la vez).

## Mejora sugerida (no implementada)
Registrar en el log el motivo cuando la IA no atiende una sala (`ai_operation_event=ai_inactive reason=paused|assigned|closed|flag_off room=...`). Costaria una linea en
`support/consumers.py` y ahorraria este diagnostico. Pendiente de decision del usuario.

## Relacionado
- Excepcion registrada a la regla 0-DEV-FIRST: consultas de solo lectura y una reactivacion en `sintel_prod_django` por autorizacion expresa del usuario.
- Mismo dia: `AUDITORIA/INCIDENTE_IA_CONFIG_LOCALHOST_2026-09-25.md`.
