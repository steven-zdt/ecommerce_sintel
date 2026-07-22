from operations.models import OperationTicket

# Transiciones de estado permitidas (FSM)
ALLOWED_TRANSITIONS = {
    OperationTicket.STATUS_CREATED: [
        OperationTicket.STATUS_DOCS_PENDING,
        OperationTicket.STATUS_READY,
        OperationTicket.STATUS_CANCELLED,
    ],
    OperationTicket.STATUS_DOCS_PENDING: [
        OperationTicket.STATUS_READY,
        OperationTicket.STATUS_CANCELLED,
    ],
    OperationTicket.STATUS_READY: [
        OperationTicket.STATUS_ASSIGNED,
        OperationTicket.STATUS_CANCELLED,
    ],
    OperationTicket.STATUS_ASSIGNED: [
        OperationTicket.STATUS_SCHEDULED,
        OperationTicket.STATUS_READY,
        OperationTicket.STATUS_CANCELLED,
    ],
    OperationTicket.STATUS_SCHEDULED: [
        OperationTicket.STATUS_EN_ROUTE,
        OperationTicket.STATUS_CANCELLED,
    ],
    OperationTicket.STATUS_EN_ROUTE: [
        OperationTicket.STATUS_IN_PROGRESS,
        OperationTicket.STATUS_CANCELLED,
    ],
    OperationTicket.STATUS_IN_PROGRESS: [
        OperationTicket.STATUS_COMPLETED,
        OperationTicket.STATUS_CANCELLED,
    ],
    OperationTicket.STATUS_COMPLETED: [],
    OperationTicket.STATUS_CANCELLED: [],
}

# Documentos que el CLIENTE debe subir (excluyendo los generados por el sistema)
CUSTOMER_REQUIRED_DOCS = {
    OperationTicket.SHOP_DELIVERY: [],
    OperationTicket.RENTAL:        ['ID_CARD'],
    OperationTicket.SERVICE:       ['ID_CARD'],
}

# Todos los documentos requeridos por tipo (incluyendo los generados por sistema)
ALL_REQUIRED_DOCS = {
    OperationTicket.SHOP_DELIVERY: ['INVOICE'],
    OperationTicket.RENTAL:        ['ID_CARD', 'RENTAL_CONTRACT'],
    OperationTicket.SERVICE:       ['ID_CARD', 'SERVICE_CONTRACT'],
}

# Mapa de estado a milestone de TrackingEvent
STATUS_TO_MILESTONE = {
    OperationTicket.STATUS_ASSIGNED:    'ASSIGNED',
    OperationTicket.STATUS_SCHEDULED:   'SCHEDULED',
    OperationTicket.STATUS_EN_ROUTE:    'EN_ROUTE',
    OperationTicket.STATUS_IN_PROGRESS: 'IN_PROGRESS',
    OperationTicket.STATUS_COMPLETED:   'COMPLETED',
    OperationTicket.STATUS_CANCELLED:   'CANCELLED',
}
