from django.contrib import admin
from .models import UserVerification, VerificationDocument, VerificationEvent, ConsentRecord

admin.site.register(UserVerification)
admin.site.register(VerificationDocument)
admin.site.register(VerificationEvent)
admin.site.register(ConsentRecord)
