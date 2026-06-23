"""Serializers de seguridad y autenticacion."""
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Permiso, Rol

Usuario = get_user_model()


class PermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permiso
        fields = ["id", "codigo", "descripcion"]


class RolSerializer(serializers.ModelSerializer):
    permisos = PermisoSerializer(many=True, read_only=True)
    permisos_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Permiso.objects.all(),
        source="permisos",
        required=False,
    )

    class Meta:
        model = Rol
        fields = [
            "id",
            "nombre",
            "descripcion",
            "estado",
            "permisos",
            "permisos_ids",
        ]


class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=4)
    roles = RolSerializer(many=True, read_only=True)
    roles_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Rol.objects.all(),
        source="roles",
        required=False,
    )
    permisos = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "correo",
            "estado",
            "is_active",
            "is_superuser",
            "ultimo_acceso",
            "roles",
            "roles_ids",
            "permisos",
            "password",
        ]
        read_only_fields = ["ultimo_acceso", "is_superuser"]

    def get_permisos(self, obj):
        return sorted(obj.codigos_permisos())

    def create(self, validated_data):
        from django.utils.crypto import get_random_string

        password = validated_data.pop("password", None)
        roles = validated_data.pop("roles", [])
        usuario = Usuario(**validated_data)
        usuario.set_password(password or get_random_string(12))
        usuario.save()
        if roles:
            usuario.roles.set(roles)
        return usuario

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        roles = validated_data.pop("roles", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if roles is not None:
            instance.roles.set(roles)
        return instance


class LoginSerializer(TokenObtainPairSerializer):
    """Login JWT que ademas devuelve datos del usuario y sus permisos."""

    def validate(self, attrs):
        data = super().validate(attrs)
        self.user.ultimo_acceso = timezone.now()
        self.user.save(update_fields=["ultimo_acceso"])
        data["usuario"] = UsuarioSerializer(self.user).data
        return data
