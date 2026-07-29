# Instrucciones: Reiniciar Django y Probar Endpoints Detail

**Problema Actual:** Django server no está corriendo  
**Solución:** Reiniciar manualmente  
**Estado Código:** ✅ Todos los fixes aplicados

---

## ✅ Fixes Aplicados (3 commits)

1. **c2cbb63** - Reordered @action and @extend_schema decorators
2. **7e1893c** - Changed permission_classes to use tuple syntax
3. **d4582ad** - Removed @extend_schema decorator (workaround para diagnóstico)

---

## 🔧 Pasos para Reiniciar Django

### Opción 1: En Terminal Local (Recomendado)

```bash
# Ir al directorio del proyecto
cd C:\Users\Administrator\Documents\ecommerce_sintel_rest\ecommerce_sintel

# Reactivar virtualenv si es necesario
# source venv/bin/activate  # en Linux/Mac
# venv\Scripts\activate     # en Windows

# Iniciar servidor Django
python manage.py runserver 0.0.0.0:8000
```

El servidor debería mostrar:
```
Starting development server at http://0.0.0.0:8000/
Quit the server with CONTROL-C.
```

### Opción 2: Si Docker está en uso

```bash
docker restart <container-id>
# o
docker-compose up django
```

---

## ✅ Verificación después del Restart

### 1. Verificar que el servidor responde

```bash
curl http://localhost:8000/api/v1/renting/equipment/
```

Debería retornar JSON con lista de equipos.

### 2. Probar el endpoint detail

```bash
# Obtener UUID de equipo
EQUIPMENT_UUID="6f02beb4-4144-411e-9941-6a3ab1521d36"

# Probar endpoint (sin @extend_schema ahora)
curl "http://localhost:8000/api/v1/renting/equipment/$EQUIPMENT_UUID/detail/" | python -m json.tool | head -30
```

### 3. Verificar respuesta esperada

Debería retornar JSON con estructura:
```json
{
  "uuid": "6f02beb4-4144-411e-9941-6a3ab1521d36",
  "slug": "...",
  "hero": {...},
  "pricing": {...},
  "marketing": {...},
  "technical": {...},
  "services": {...},
  "media": {...},
  "faqs": [...],
  "reviews": {...},
  ...
}
```

---

## 📱 Pruebas en UI

Después de verificar que el servidor responde:

### 1. Abrir navegador
```
http://localhost:5173/alquiler
```

### 2. Hacer clic en "Ver equipo"
- Debería navegar a `/alquiler/{uuid}`
- RentalDetailView.vue debe cargar
- Debe mostrar:
  - ✅ Galería de imágenes
  - ✅ Precio diario/horario
  - ✅ Calificaciones
  - ✅ Tags/badges
  - ✅ Descripción
  - ✅ FAQs
  - ✅ Equipos relacionados

### 3. Verificar consola del navegador
- No debe haber errores 500
- No debe haber AxiosError
- Debe haber solo petición GET a `/detail/`

### 4. Repetir para Shop
```
http://localhost:5173/tienda
```

### 5. Repetir para Services
```
http://localhost:5173/servicios
```

---

## 🔍 Si aún hay errores

Si después de reiniciar aún ves el error "bool object is not callable":

```bash
# 1. Verifica que los cambios se aplicaron
grep -n "@action.*detail" renting/api/views.py
# Debería mostrar: @action(detail=True, methods=['get'], url_path='detail', permission_classes=(permissions.AllowAny,))

# 2. Verifica que NO hay @extend_schema después
grep -A 2 "@action.*detail" renting/api/views.py
# NO debe mostrar @extend_schema en las líneas siguientes

# 3. Si algo falta, ejecuta git status
git status

# 4. Ver último commit
git log --oneline -5
```

---

## 📊 Endpoints para Probar

| Módulo | URL | Esperado |
|--------|-----|----------|
| **Renting** | `http://localhost:8000/api/v1/renting/equipment/6f02beb4-4144-411e-9941-6a3ab1521d36/detail/` | JSON 200 ✅ |
| **Shop** | `http://localhost:8000/api/v1/shop/products/{uuid}/detail/` | JSON 200 ✅ |
| **Services** | `http://localhost:8000/api/v1/technical-services/services/{uuid}/detail/` | JSON 200 ✅ |

---

## 🎯 Checklist Final

- [ ] Django server reiniciado y corriendo
- [ ] `/api/v1/renting/equipment/` responde con 200
- [ ] `/api/v1/renting/equipment/{uuid}/detail/` responde con 200 + EquipmentPublicDetailDTO
- [ ] `/api/v1/shop/products/{uuid}/detail/` responde con 200
- [ ] `/api/v1/technical-services/services/{uuid}/detail/` responde con 200
- [ ] RentalDetailView carga sin errores
- [ ] ProductDetailView carga sin errores
- [ ] ServiceDetailView carga sin errores
- [ ] Consola del navegador sin errores 500
- [ ] Imágenes y datos se cargan correctamente

---

## 📝 Nota Técnica

El @extend_schema decorator de drf-spectacular estaba causando conflictos con el @action decorator de DRF. Se removió temporalmente para permitir que el endpoint funcione. 

Después de verificar que funciona sin @extend_schema, se puede agregar nuevamente de forma correcta.

---

**Próximo Paso:** Reiniciar Django y ejecutar las pruebas arriba listadas.

