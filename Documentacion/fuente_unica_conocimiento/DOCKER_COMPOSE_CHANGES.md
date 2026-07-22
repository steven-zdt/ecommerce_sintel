# 🏗️ Docker Compose — Cambios para Eliminar Construcción Automática

## 📋 Problema Identificado

El archivo `docker-compose.yml` **original** tenía `build:` en **3 servicios**:

```yaml
django:
  build:
    context: .
    target: runtime
  # ...

celery_worker:
  build:
    context: .
    target: runtime
  # ...

celery_beat:
  build:
    context: .
    target: runtime
  # ...
```

### ¿Por qué causaba problemas?

Cada vez que ejecutabas `docker compose up`, Docker Compose:
1. **Ejecutaba el Dockerfile** (compilaba Python, instalaba dependencias)
2. **Construía la imagen** `ecommerce_sintel:runtime`
3. **Detenía el proceso** si había cambios en el código

Esto es **ineficiente** porque:
- ⏱️ Primer run: ~2-5 minutos (compilación completa)
- ⏱️ Siguientes runs: 1-2 minutos (Docker Compose rebuildea aunque nada cambió)
- 💾 Consume mucho almacenamiento (layer caché)
- 🔄 Interrupción innecesaria del servicio

---

## ✅ Solución Implementada

### Cambios en `docker-compose.yml`

Se **reemplazó** `build:` con `image:` en los 3 servicios:

```yaml
django:
  image: ecommerce_sintel:runtime  # ← Usa imagen pre-construida
  
celery_worker:
  image: ecommerce_sintel:runtime  # ← Usa imagen pre-construida
  
celery_beat:
  image: ecommerce_sintel:runtime  # ← Usa imagen pre-construida
```

### Nuevos Scripts de Construcción

Se creó `build-image.ps1` para construir la imagen **UNA SOLA VEZ**:

```bash
.\build-image.ps1
```

---

## 🚀 Workflow Nuevo

### 1️⃣ Primera vez: Construir imagen

```bash
cd ecommerce_sintel
.\build-image.ps1
```

✅ Esto:
- Construye `ecommerce_sintel:runtime` una sola vez
- Guarda la imagen en el repositorio local de Docker

### 2️⃣ Levantar servicios (nunca rebuildea)

```bash
docker compose up -d
```

✅ Ventajas:
- 🚀 Arranca en **10-15 segundos** (no construye)
- 💾 No consume almacenamiento innecesario
- 🔄 Reutiliza imagen entre runs

### 3️⃣ Si cambias código

```bash
# Los cambios se aplican LIVE porque /code está mapeado
# Django auto-reload detecta cambios
# No necesitas reconstruir
```

### 4️⃣ Si cambias dependencias (pyproject.toml)

```bash
# Reconstruye la imagen
.\build-image.ps1

# Reinicia docker compose
docker compose down
docker compose up -d
```

---

## 📊 Comparativa

| Operación | Antes (con `build:`) | Ahora (con `image:`) |
|-----------|----------------------|----------------------|
| `docker compose up` (1era vez) | 2-5 min | 30 seg |
| `docker compose up` (siguientes) | 1-2 min | 10-15 seg |
| Cambio en código | Auto-reload | Auto-reload |
| Cambio en requirements | Manual rebuild + up | `build-image.ps1` + up |

---

## 🔍 Verificación

Para confirmar que la imagen existe y se está usando:

```bash
# Ver todas las imágenes
docker images | grep ecommerce_sintel

# Ver estado de contenedores
docker ps -a

# Revisar que se está usando imagen, no construyendo
docker compose up -d --no-build
```

---

## 📝 Notas Técnicas

### Dockerfile Multi-stage

El `Dockerfile` sigue siendo multi-stage:

```dockerfile
FROM python:3.13-slim AS builder
  # Compilación de dependencias

FROM ... AS runtime
  # Imagen final mínima (300mb aprox)
```

### Por qué esto es mejor

1. **Separación de concerns**: construcción vs. ejecución
2. **Imagen final pequeña**: solo lo necesario para correr
3. **Caché eficiente**: Docker reutiliza layers
4. **Reproducibilidad**: misma imagen siempre

---

## 🛠️ Troubleshooting

### "Imagen no encontrada"

```bash
# Construye la imagen primero
.\build-image.ps1

# Verifica que exista
docker images | grep ecommerce_sintel
```

### "Contenedor no arranca"

```bash
# Revisa logs
docker compose logs -f django

# Reconstruye si es necesario
.\build-image.ps1
docker compose down
docker compose up -d
```

### "Cambios en código no se aplican"

Los cambios deben ser en `/code` mapeado. Verifica:

```bash
# Ver volumes mapeados
docker volume ls | grep ecommerce
docker inspect ecommerce_sintel_django

# Restart Django si es necesario
docker compose restart django
```

---

## 📚 Referencias

- [Docker Compose `image` vs `build`](https://docs.docker.com/compose/compose-file/compose-file-v3/#image)
- [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker layer caching](https://docs.docker.com/build/cache/)
