"""Modelos de seguridad: Usuario, Rol, Permiso y relaciones."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Permiso(models.Model):
    """Permiso atomico identificado por un codigo (p.ej. 'compras.crear')."""

    codigo = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "permiso"
        ordering = ["codigo"]

    def __str__(self):
        return self.codigo


class Rol(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    descripcion = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=20, default="ACTIVO")
    permisos = models.ManyToManyField(
        Permiso, through="RolPermiso", related_name="roles"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rol"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class RolPermiso(models.Model):
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, db_column="idRol")
    permiso = models.ForeignKey(
        Permiso, on_delete=models.CASCADE, db_column="idPermiso"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rol_permiso"
        unique_together = ("rol", "permiso")


class Usuario(AbstractUser):
    """
    Usuario del sistema. Extiende AbstractUser de Django: el password usa el
    hashing seguro de Django (no el VARCHAR(50) del documento). El campo
    `username` cumple el rol del campo `usuario` del modelo original.
    """

    correo = models.EmailField("correo", max_length=254, blank=True)
    estado = models.CharField(max_length=20, default="ACTIVO")
    ultimo_acceso = models.DateTimeField(
        db_column="ultimoAcceso", null=True, blank=True
    )
    roles = models.ManyToManyField(
        Rol, through="UsuarioRol", related_name="usuarios"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "usuario"
        ordering = ["username"]

    def codigos_permisos(self):
        """Conjunto de codigos de permiso otorgados por los roles del usuario."""
        if self.is_superuser:
            return set(Permiso.objects.values_list("codigo", flat=True))
        return set(
            Permiso.objects.filter(roles__usuarios=self)
            .values_list("codigo", flat=True)
            .distinct()
        )

    def tiene_permiso(self, codigo):
        return self.is_superuser or self.roles.filter(
            permisos__codigo=codigo
        ).exists()


class UsuarioRol(models.Model):
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, db_column="idUsuario"
    )
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, db_column="idRol")
    fecha_asignacion = models.DateTimeField(
        db_column="fechaAsignacion", auto_now_add=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "usuario_rol"
        unique_together = ("usuario", "rol")
