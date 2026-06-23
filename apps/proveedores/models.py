from django.db import models


class Proveedor(models.Model):
    nombre = models.CharField(max_length=160)
    nit = models.CharField(max_length=40, blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    correo = models.EmailField(max_length=254, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=20, default="ACTIVO")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "proveedor"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
