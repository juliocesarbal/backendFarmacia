"""
Carga inicial: roles, permisos, usuario admin, categorias, unidades y motivos
de baja de ejemplo. Idempotente (usa get_or_create).

    python manage.py seed_inicial
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bajas.models import MotivoBaja
from apps.catalogos.models import CategoriaProducto, UnidadMedida
from apps.users.models import Permiso, Rol, Usuario

# Permisos base del sistema (codigo: descripcion)
PERMISOS = {
    "usuarios.ver": "Ver usuarios",
    "usuarios.crear": "Crear usuarios",
    "usuarios.editar": "Editar usuarios",
    "usuarios.eliminar": "Eliminar usuarios",
    "roles.ver": "Ver roles",
    "roles.crear": "Crear roles",
    "roles.editar": "Editar roles",
    "roles.eliminar": "Eliminar roles",
    "productos.crear": "Crear productos",
    "productos.editar": "Editar productos",
    "productos.anular": "Anular/restaurar productos",
    "catalogos.gestionar": "Gestionar categorias y unidades",
    "proveedores.crear": "Crear proveedores",
    "proveedores.editar": "Editar proveedores",
    "compras.crear": "Registrar compras",
    "compras.editar": "Editar compras",
    "compras.confirmar": "Confirmar compras",
    "ventas.crear": "Registrar ventas",
    "ventas.editar": "Editar ventas",
    "ventas.confirmar": "Confirmar ventas",
    "ventas.anular": "Anular ventas",
    "bajas.crear": "Registrar bajas",
    "bajas.editar": "Editar bajas",
    "bajas.confirmar": "Confirmar bajas",
    "bajas.gestionar": "Gestionar motivos de baja",
    "ajustes.crear": "Registrar ajustes",
    "ajustes.editar": "Editar ajustes",
    "ajustes.confirmar": "Confirmar ajustes",
    "kardex.ver": "Consultar Kardex",
    "reportes.ver": "Ver reportes",
    "importaciones.gestionar": "Importar datos historicos",
    "analitica.ejecutar": "Ejecutar analitica K-means",
    "trazabilidad.ver": "Consultar trazabilidad",
}

# Rol -> lista de codigos (o "*" para todos)
ROLES = {
    "Administrador del Sistema": "*",
    "Encargado/a de Farmacia": [
        "productos.crear", "productos.editar", "productos.anular",
        "catalogos.gestionar", "proveedores.crear", "proveedores.editar",
        "compras.crear", "compras.editar", "compras.confirmar",
        "ventas.crear", "ventas.editar", "ventas.confirmar", "ventas.anular",
        "bajas.crear", "bajas.editar", "bajas.confirmar", "bajas.gestionar",
        "ajustes.crear", "ajustes.editar", "ajustes.confirmar",
        "kardex.ver", "reportes.ver", "importaciones.gestionar",
        "analitica.ejecutar", "trazabilidad.ver",
    ],
    "Personal de Farmacia": [
        "ventas.crear", "ventas.confirmar", "productos.crear", "kardex.ver",
        "reportes.ver",
    ],
    "Contabilidad": ["kardex.ver", "reportes.ver", "trazabilidad.ver"],
    "Auditoria": ["kardex.ver", "reportes.ver", "trazabilidad.ver"],
    "Direccion/Coordinacion": ["reportes.ver", "kardex.ver"],
}

CATEGORIAS = ["Antibioticos", "Analgesicos", "Antiparasitarios", "Material de curacion", "Insumos"]
UNIDADES = [("Unidad", "UND"), ("Caja", "CJA"), ("Frasco", "FCO"), ("Mililitro", "ML"), ("Comprimido", "COMP")]
MOTIVOS_BAJA = ["Vencimiento", "Deterioro", "Perdida", "Uso interno", "Aplicacion en consultorio"]


class Command(BaseCommand):
    help = "Carga datos iniciales (roles, permisos, admin, catalogos demo)."

    @transaction.atomic
    def handle(self, *args, **options):
        # Permisos
        permisos = {}
        for codigo, desc in PERMISOS.items():
            permisos[codigo], _ = Permiso.objects.get_or_create(
                codigo=codigo, defaults={"descripcion": desc}
            )
        self.stdout.write(self.style.SUCCESS(f"Permisos: {len(permisos)}"))

        # Roles
        for nombre, codigos in ROLES.items():
            rol, _ = Rol.objects.get_or_create(nombre=nombre)
            if codigos == "*":
                rol.permisos.set(permisos.values())
            else:
                rol.permisos.set([permisos[c] for c in codigos if c in permisos])
        self.stdout.write(self.style.SUCCESS(f"Roles: {len(ROLES)}"))

        # Usuario admin
        if not Usuario.objects.filter(username="admin").exists():
            admin = Usuario.objects.create_superuser(
                username="admin", password="admin123", correo="admin@farmacia.local",
                first_name="Administrador", last_name="Sistema",
            )
            admin.roles.add(Rol.objects.get(nombre="Administrador del Sistema"))
            self.stdout.write(self.style.SUCCESS("Usuario admin / admin123 creado"))
        else:
            self.stdout.write("Usuario admin ya existe")

        # Catalogos demo
        for nombre in CATEGORIAS:
            CategoriaProducto.objects.get_or_create(nombre=nombre)
        for nombre, abrev in UNIDADES:
            UnidadMedida.objects.get_or_create(nombre=nombre, defaults={"abreviatura": abrev})
        for nombre in MOTIVOS_BAJA:
            MotivoBaja.objects.get_or_create(nombre=nombre)
        self.stdout.write(self.style.SUCCESS("Catalogos demo cargados"))
        self.stdout.write(self.style.SUCCESS("Seed completado."))
