from django.utils import timezone


def transition_operation(*, model_class, transitions_map, operation, target_status,
                          apply_extra_fields=None):
    """
    Nucleo compartido de FSM de Operaciones (DUP-B2/DT-L8): lock de fila + guard
    via diccionario de adyacencia (`transitions_map`) + guardado con
    update_fields dinamico. Usado por renting.RentalOperationCommands.transition()
    y technical_services.ServiceOperationCommands.transition() -- las unicas 2 de
    las 3 FSM del proyecto que comparten esta forma exacta (Shipment, en
    orders/services/fulfillment/, esta arquitecturado distinto: N metodos con
    nombre propio en vez de un dispatcher generico via diccionario de transiciones,
    y sincroniza 2 modelos a la vez -- no encaja en este patron, no se forzo).

    Deliberadamente NO crea el evento de auditoria ni ejecuta los side-effects de
    dominio (sync de RentalPeriod/RentalRequest, ServiceTimelineCommands,
    liberacion de slots de disponibilidad, notificaciones) -- esos siguen
    viviendo en cada Commands.transition(), que llama a esto primero y despues
    hace su propio trabajo especifico, dentro de su propio @transaction.atomic
    (este helper no abre transaccion propia, confia en la del caller).

    apply_extra_fields, si se pasa, recibe (operation, target_status, now) y debe
    mutar `operation` y devolver la lista de nombres de campo adicionales a
    incluir en save(update_fields=...) -- ver ServiceOperationCommands.transition()
    para el caso real (arrived_at/started_at/completed_at segun target_status).
    RentalOperationCommands.transition() no necesita ninguno, lo omite.
    """
    operation = model_class.objects.select_for_update().get(pk=operation.pk)
    allowed = transitions_map.get(operation.status, set())
    if target_status not in allowed:
        raise ValueError(f'Transicion invalida: {operation.status} -> {target_status}.')
    operation.status = target_status
    update_fields = ['status', 'updated_at']
    if apply_extra_fields:
        now = timezone.now()
        update_fields += apply_extra_fields(operation, target_status, now)
    operation.save(update_fields=update_fields)
    return operation
