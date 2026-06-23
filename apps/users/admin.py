from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Permiso, Rol, RolPermiso, Usuario, UsuarioRol


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "correo", "estado", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Farmacia", {"fields": ("correo", "estado", "ultimo_acceso")}),
    )


admin.site.register(Rol)
admin.site.register(Permiso)
admin.site.register(RolPermiso)
admin.site.register(UsuarioRol)
