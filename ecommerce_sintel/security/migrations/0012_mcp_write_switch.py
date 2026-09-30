from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('security', '0011_mcp_access_tokens'),
    ]

    operations = [
        migrations.AddField(
            model_name='mcpaccesstoken',
            name='write_enabled_until',
            field=models.DateTimeField(blank=True, help_text='Interruptor de escritura: mientras sea futuro, el servidor MCP le da a este token el perfil ADMIN_CRUD. Solo lo cambia el admin con sesion normal.', null=True),
        ),
        migrations.AlterField(
            model_name='securityevent',
            name='event_type',
            field=models.CharField(choices=[('LOGIN_SUCCESS', 'Login exitoso'), ('LOGIN_FAILED', 'Login fallido'), ('KYC_REJECTED', 'KYC rechazado'), ('KYC_BLOCKED', 'KYC bloqueado'), ('RATE_LIMIT_HIT', 'Limite de tasa alcanzado'), ('FILE_REJECTED', 'Archivo rechazado'), ('PAYMENT_WEBHOOK_INVALID_SIGNATURE', 'Webhook de pago con firma invalida'), ('PAYMENT_APPROVED', 'Pago aprobado'), ('PAYMENT_DECLINED', 'Pago rechazado'), ('PAYMENT_CARD_REMOVED', 'Tarjeta guardada eliminada'), ('PAYMENT_TRANSACTION_ABANDONED', 'Transaccion de pago abandonada (sin wompi_id tras el umbral)'), ('PAYMENT_FEATURE_FLAG_CHANGED', 'Flag operativo de pagos modificado'), ('COUPON_REJECTED', 'Cupon invalido rechazado'), ('INVENTORY_MANUAL_ADJUSTMENT', 'Ajuste manual de inventario'), ('OPERATION_FORCE_CANCELLED', 'Operacion cancelada forzosamente'), ('NOTIFICATION_CHANNEL_FAILED', 'Canal de notificacion con fallo permanente'), ('AI_ACTION_EXECUTED', 'Accion de escritura ejecutada por el AI Core'), ('ADMIN_RESOURCE_DELETED', 'Recurso eliminado desde el panel administrativo'), ('PAYMENT_SYNC_REFERENCE_MISMATCH', 'Reconciliacion de pago rechazada: reference/monto no coincide'), ('AI_PROVIDER_CREATED', 'Proveedor de IA creado'), ('AI_PROVIDER_UPDATED', 'Proveedor de IA actualizado'), ('AI_PROVIDER_ACTIVATED', 'Proveedor de IA activado'), ('AI_PROVIDER_DEACTIVATED', 'Proveedor de IA desactivado'), ('AI_PROVIDER_TESTED', 'Conexion de proveedor de IA probada'), ('AI_MODEL_CHANGED', 'Modelo de IA agregado/eliminado'), ('AI_CHANNEL_CHANGED', 'Configuracion de canal de IA modificada (primario/fallback)'), ('AI_SECURITY_FLAG', 'Senal de seguridad en un turno de IA (fuga bloqueada, secreto redactado, inyeccion)'), ('MCP_TOKEN_CREATED', 'Token personal del servidor MCP creado'), ('MCP_TOKEN_REVOKED', 'Token personal del servidor MCP revocado'), ('MCP_TOKEN_EXCHANGED', 'Token del servidor MCP canjeado por un JWT corto'), ('MCP_TOKEN_EXCHANGE_FAILED', 'Canje de token MCP rechazado (invalido, revocado, caducado o sin permisos)'), ('MCP_WRITE_ENABLED', 'Escritura (ADMIN_CRUD) activada para un token MCP'), ('MCP_WRITE_DISABLED', 'Escritura (ADMIN_CRUD) desactivada para un token MCP'), ('MCP_ACTION', 'Accion ejecutada por un cliente MCP')], db_index=True, max_length=40),
        ),
    ]
