import os
import uuid
from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateKycStorage(FileSystemStorage):
    """
    Storage fuera de MEDIA_ROOT -- ni el static() de Django en DEBUG ni el
    alias /media/ de nginx en produccion lo exponen. base_url=None fuerza a
    que el unico acceso posible sea el endpoint autenticado de descarga
    (VerificationDocumentViewSet.download), nunca una URL publica directa.
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('location', settings.KYC_PRIVATE_STORAGE_ROOT)
        kwargs.setdefault('base_url', None)
        super().__init__(*args, **kwargs)


def kyc_private_storage():
    return PrivateKycStorage()


def kyc_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"{instance.verification.user.uuid}/{instance.doc_type}/{uuid.uuid4().hex}{ext}"
