# Backend Farmacia — Sistema de Gestión Farmacéutica (HEV-UAGRM)

API REST en Django + Django REST Framework para el Sistema Web de Gestión Farmacéutica
del Hospital Escuela de Veterinaria (UAGRM), con automatización de **Kardex valorado
por PEPS/FIFO** y análisis de medicamentos con K-means.

## Requisitos
- Python 3.13+
- PostgreSQL 17 (servicio corriendo)

## Puesta en marcha

```powershell
# 1. Activar entorno virtual
venv\Scripts\activate

# 2. Configurar variables de entorno
copy .env.example .env   # luego edita .env con tu DB_PASSWORD y SECRET_KEY

# 3. Crear la base de datos en PostgreSQL (una sola vez)
#    psql -U postgres -c "CREATE DATABASE farmacia_db;"

# 4. Migraciones
python manage.py migrate

# 5. Datos iniciales (roles, permisos, admin, catálogos demo)
python manage.py seed_inicial

# 6. Levantar el servidor
python manage.py runserver
```

## URLs útiles
- API base: http://localhost:8000/api/
- Swagger / OpenAPI: http://localhost:8000/api/docs/
- Admin Django: http://localhost:8000/admin/

## Arquitectura
La lógica de negocio (FIFO, Kardex, anulaciones) vive en `services.py` de cada app,
**no** en las views. Toda operación que afecta inventario es atómica
(`transaction.atomic`) y registra trazabilidad en la bitácora.

Apps: `users, catalogos, proveedores, inventario, compras, ventas, bajas,
ajustes, kardex, importaciones, reportes, analitica, auditoria`.
