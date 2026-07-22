import hashlib
from dataclasses import dataclass


@dataclass
class ScanResult:
    status: str
    detail: str = ''


class DocumentScanner:
    """
    Punto de extension para antivirus real (ej. ClamAV via clamd) en una fase
    futura. En esta fase es un passthrough: siempre retorna SKIPPED. Reemplazar
    el cuerpo de scan() por un cliente clamd real no requiere tocar ningun
    caller -- solo KycCommands.upload_document llama a esto.
    """

    @staticmethod
    def scan(file) -> ScanResult:
        return ScanResult(status='SKIPPED', detail='Antivirus no configurado en esta fase.')

    @staticmethod
    def sha256_of(file) -> str:
        hasher = hashlib.sha256()
        for chunk in file.chunks():
            hasher.update(chunk)
        file.seek(0)
        return hasher.hexdigest()
