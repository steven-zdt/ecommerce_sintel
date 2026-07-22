from django.contrib import admin
from .models import (
    DispatcherProfile, OperationTicket, OperationAssignment,
    TrackingEvent, OperationDocument, OperationReview,
)

admin.site.register(DispatcherProfile)
admin.site.register(OperationTicket)
admin.site.register(OperationAssignment)
admin.site.register(TrackingEvent)
admin.site.register(OperationDocument)
admin.site.register(OperationReview)
