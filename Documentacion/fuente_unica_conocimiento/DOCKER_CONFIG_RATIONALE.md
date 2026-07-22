# Docker Configuration Rationale — E-Commerce Sintel REST
**Last Updated:** 2026-04-16  
**Project:** ecommerce_sintel  
**Status:** ✅ COMPLETAMENTE AISLADO

---

## ¿Cuál era el problema?

El proyecto estaba levantando ACCIDENTALMENTE contenedores de `secop_system` cuando se ejecutaba `docker compose up`. Esto sucedía porque:

1. ❌ El `docker-compose.yml` NO tenía un nombre de proyecto explícito → Docker usaba el nombre de la carpeta
2. ❌ Los contenedores NO tenían prefijos → Fácil de confundir con otros proyectos
3. ❌ Los volúmenes NO tenían nombres únicos → Potencial conflicto de datos
4. ❌ No había network privada → Posible interferencia entre proyectos
5. ❌ Faltaban comentarios de seguridad → Riesgo de modificaciones futuras

---

## Soluciones Implementadas

### 1. **`docker-compose.yml` — Aislamiento Total**

#### ANTES (Riesgoso):
```yaml
services:
  redis:
    image: redis:7.2-alpine
    ports: ["6380:6379"]
    volumes:
      - redis_data:/data  # ← Compartido globalmente

  django:
    # ...
    volumes:
      - static_volume:/code/staticfiles  # ← Compartido

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

#### DESPUÉS (Seguro):
```yaml
name: ecommerce_sintel  # ← Explícito: evita conflictos

services:
  redis:
    image: redis:7.2-alpine
    container_name: ecommerce_sintel_redis  # ← Prefijado
    ports: ["6380:6379"]
    volumes:
      - ecommerce_sintel_redis_data:/data  # ← Único a este proyecto
    networks:
      - ecommerce_sintel_network  # ← Red privada

  db:
    container_name: ecommerce_sintel_db  # ← Prefijado
    # ... autres services ...

volumes:
  ecommerce_sintel_postgres_data:  # ← Prefijado
  ecommerce_sintel_redis_data:     # ← Prefijado
  ecommerce_sintel_static_volume:  # ← Prefijado
  ecommerce_sintel_media_volume:   # ← Prefijado
  ecommerce_sintel_beat_schedule:  # ← Prefijado

networks:
  ecommerce_sintel_network:  # ← Red privada bridge
    driver: bridge
    name: ecommerce_sintel_network
```

### 2. **`Dockerfile` — Comentarios de Aislamiento**

Agregados comentarios al inicio y al final indicando:
- Pertenece ÚNICAMENTE a ecommerce_sintel
- Es independiente de secop_system y otros proyectos
- Imagen final mínima sin contaminación

---

## Cambios Exactos Realizados

| Archivo | Cambio | Razón |
|---------|--------|-------|
| `docker-compose.yml` (L1-17) | ✅ Agregado header con explicación | Seguridad: clarificar alcance |
| `docker-compose.yml` (L19) | ✅ `name: ecommerce_sintel` | Nombre EXPLÍCITO del proyecto |
| `docker-compose.yml` (L27) | ✅ `container_name: ecommerce_sintel_redis` | Identificación unívoca |
| `docker-compose.yml` (L30) | ✅ `ecommerce_sintel_redis_data:/data` | Volumen prefijado |
| `docker-compose.yml` (L37) | ✅ `networks: - ecommerce_sintel_network` | Red privada |
| `docker-compose.yml` (L41) | ✅ `container_name: ecommerce_sintel_db` | Identificación unívoca |
| `docker-compose.yml` (L51) | ✅ `ecommerce_sintel_postgres_data` | Volumen prefijado |
| `docker-compose.yml` (L54) | ✅ `networks: - ecommerce_sintel_network` | Red privada |
| Todos los services | ✅ Container names + network | Aislamiento |
| `docker-compose.yml` (L182-210) | ✅ Sección `volumes:` con prefijos | Datos únicos |
| `docker-compose.yml` (L215-220) | ✅ Sección `networks:` privada | Bridge network |
| `Dockerfile` (L1-12) | ✅ Header de aislamiento | Seguridad: propósito claro |
| `Dockerfile` (L86-91) | ✅ Footer de aislamiento | Seguridad: confirmación |

---

## Verificación de Aislamiento

### Comando 1: Verificar nombre del proyecto
```bash
docker compose config --format json | jq '.name'
# Respuesta esperada: "ecommerce_sintel"
```

### Comando 2: Listar SOLO contenedores de ecommerce_sintel
```bash
docker compose ps
# Respuesta esperada: 6 contenedores prefijados ecommerce_sintel_*
```

### Comando 3: Listar volúmenes de ecommerce_sintel
```bash
docker volume ls | grep ecommerce_sintel
# Respuesta esperada: 5 volúmenes prefijados
```

### Comando 4: Verificar network privada
```bash
docker network ls | grep ecommerce_sintel_network
# Respuesta esperada: 1 network bridge privada
```

### Comando 5: Escaneo de seguridad (cero referencias a otros proyectos)
```bash
docker compose config | grep -i "secop_system" || echo "✅ Clean"
# Respuesta esperada: "✅ Clean"
```

---

## Por Qué Esto Funciona

### Antes (Problema)
```
$ docker compose up
→ Docker busca el nombre del proyecto
→ No encuentra en docker-compose.yml
→ Asumeapunta al folder: "ecommerce_sintel"
→ Pero si hay problemas de contexto, puede usar el proyecto anterior: "secop_system"
→ Resultado: Levanta contenedores confundidos
```

### Después (Solución)
```
$ docker compose up
→ Docker lee: name: ecommerce_sintel (EXPLÍCITO en L19)
→ Crea contenedores: ecommerce_sintel_redis, ecommerce_sintel_db, etc.
→ Crea network: ecommerce_sintel_network
→ Crea volúmenes: ecommerce_sintel_postgres_data, etc.
→ IMPOSIBLE confundir con secop_system
```

---

## Health Checks en Cascada (Mejora Adicional)

Los servicios se levantan en orden correcto debido a `depends_on` with `condition: service_healthy`:

```
1. PostgreSQL 16 inicia
   └─ Espera a que responda healthcheck

2. Redis 7.2 inicia
   └─ Espera a que responda healthcheck

3. Django inicia (una vez DB + Redis estén healthy)
   └─ Espera a que responda healthcheck

4. Celery Worker inicia (una vez Django esté healthy)
   └─ Comienza a procesar tareas

5. Celery Beat inicia (una vez Django esté healthy)
   └─ Comienza a agendar tareas

6. Nginx inicia (una vez Django esté healthy)
   └─ Actúa como reverse proxy
```

Sin esto, los servicios podrían intentar conectarse a dependencias no listas → crashes cascada.

---

## Checklist de Operación Segura

✅ **Antes de levantar el proyecto:**
- [ ] Detener TODOS los proyectos: `docker compose -p secop_system down --remove-orphans`
- [ ] Limpiar contenedores residuales: `docker container prune -f`
- [ ] Navegar a la carpeta correcta: `c:\Users\Administrator\Documents\ecommerce_sintel_rest\ecommerce_sintel`

✅ **Levantar ecommerce_sintel:**
- [ ] `docker compose up -d`
- [ ] Esperar a que Django esté healthy (40s aprox)
- [ ] Verificar: `docker compose ps` (6 servicios activos)

✅ **Verificar aislamiento:**
- [ ] `docker compose logs django` (sin errores)
- [ ] `curl http://localhost:8000/api/v1/health/` (respuesta 200)
- [ ] `docker volume ls | grep ecommerce_sintel` (5 volúmenes)

✅ **Parar sin interferencias:**
- [ ] `docker compose down` (SOLO afecta ecommerce_sintel)
- [ ] `docker ps` (ningún contenedor ecommerce_sintel activo)

---

## Referencias

- **Docker Compose Documentation**: [Compose Project Name](https://docs.docker.com/compose/compose-file/03-compose-file/)
- **Docker Networks**: [Networking in Compose](https://docs.docker.com/compose/networking/)
- **Health Checks**: [Healthchecks in Docker](https://docs.docker.com/engine/reference/builder/#healthcheck)

---

## Conclusión

**ANTES:** Proyecto vulnerable a cross-contamination con otros proyectos  
**DESPUÉS:** Proyecto herméticamente sellado con nombre explícito, contenedores prefijados, network privada y volúmenes únicos

🛡️ **AISLAMIENTO GARANTIZADO** ✅
