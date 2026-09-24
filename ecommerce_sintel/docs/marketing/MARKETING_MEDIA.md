# MARKETING_MEDIA

Modelo `CampaignMedia` (media_type IMAGE|VIDEO, file, mime_type, size, width, height, duration,
file_hash SHA-256, sort_order, is_active). No existia sistema de media compartido; replica el patron
por dominio del proyecto con un unico modelo para ambos tipos.

## Validacion (`marketing/services/commands.py`)
- Imagen: decodificacion real con Pillow (`verify()`), formatos JPEG/PNG/WEBP, dimensiones reales,
  maximo `MARKETING_MEDIA_MAX_IMAGE_MB` (5).
- Video: solo `.mp4` / `video/mp4`, maximo `MARKETING_MEDIA_MAX_VIDEO_MB` (100). Duracion, dimensiones
  y codec NO se validan (sin libreria de metadata de video en el proyecto; gap documentado).
- Procesamiento sincrono (ningun dominio del proyecto usa Celery para uploads).

## Endpoints (multipart, IsAdminUser)
`POST campaigns/<uuid>/media/` (file, media_type), `POST .../media/reorder/` (ordered_uuids),
`POST .../media/<uuid>/toggle/`, `DELETE .../media/<uuid>/`. Editar campos de texto de la campana nunca
toca la galeria.
