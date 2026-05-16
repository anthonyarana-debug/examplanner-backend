from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import Estudiante, Tarea, Examen


class RegistroSerializer(serializers.ModelSerializer):
    """
    Registro de nuevo estudiante.
    Valida que el correo sea @tecsup.edu.pe.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirmacion = serializers.CharField(write_only=True)

    class Meta:
        model = Estudiante
        fields = ['email', 'nombre', 'password', 'password_confirmacion']

    def validate_email(self, value):
        if not value.endswith('@tecsup.edu.pe'):
            raise serializers.ValidationError(
                'Solo se permiten correos institucionales de Tecsup (@tecsup.edu.pe)'
            )
        return value.lower()

    def validate(self, data):
        if data['password'] != data['password_confirmacion']:
            raise serializers.ValidationError({'password': 'Las contraseñas no coinciden'})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirmacion')
        password = validated_data.pop('password')
        estudiante = Estudiante(**validated_data)
        estudiante.set_password(password)
        estudiante.save()
        return estudiante


class LoginSerializer(serializers.Serializer):
    """
    Login con email y contraseña.
    Devuelve datos del estudiante para mostrar en pantalla principal.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email', '').lower()
        password = data.get('password')
        estudiante = authenticate(username=email, password=password)
        if not estudiante:
            raise serializers.ValidationError(
                'Usuario o contraseña incorrectos'
            )
        if not estudiante.is_active:
            raise serializers.ValidationError('Cuenta inactiva')
        data['estudiante'] = estudiante
        return data


class EstudianteSerializer(serializers.ModelSerializer):
    """
    Datos del estudiante para respuestas de la API.
    """
    class Meta:
        model = Estudiante
        fields = ['id', 'email', 'nombre', 'canvas_conectado', 'fecha_registro']
        read_only_fields = ['id', 'fecha_registro']


class TareaSerializer(serializers.ModelSerializer):
    """
    Tarea con días restantes calculados automáticamente.
    """
    dias_restantes = serializers.IntegerField(read_only=True)
    esta_vencida = serializers.BooleanField(read_only=True)

    class Meta:
        model = Tarea
        fields = [
            'id', 'nombre', 'curso', 'fecha_limite', 'completada',
            'fecha_completada', 'origen', 'canvas_id', 'descripcion',
            'dias_restantes', 'esta_vencida', 'fecha_creacion'
        ]
        read_only_fields = ['id', 'origen', 'canvas_id', 'fecha_completada', 'fecha_creacion']

    def validate_fecha_limite(self, value):
        """Advertencia si la fecha ya pasó (no bloquea, solo informa)."""
        if value < timezone.now():
            raise serializers.ValidationError(
                'La fecha límite ya pasó. ¿Estás seguro de que quieres registrarla?'
            )
        return value


class TareaCompletarSerializer(serializers.ModelSerializer):
    """
    Solo para marcar o desmarcar una tarea como completada.
    """
    class Meta:
        model = Tarea
        fields = ['id', 'completada', 'fecha_completada']
        read_only_fields = ['id', 'fecha_completada']


class ExamenSerializer(serializers.ModelSerializer):
    """
    Examen con días restantes y flag de próximo (menos de 48h).
    """
    dias_restantes = serializers.IntegerField(read_only=True)
    proximo = serializers.BooleanField(read_only=True)

    class Meta:
        model = Examen
        fields = [
            'id', 'curso', 'fecha', 'descripcion', 'origen',
            'canvas_id', 'dias_restantes', 'proximo', 'fecha_creacion'
        ]
        read_only_fields = ['id', 'origen', 'canvas_id', 'fecha_creacion']

    def validate_fecha(self, value):
        if value < timezone.now():
            raise serializers.ValidationError(
                'La fecha del examen ya pasó. ¿Estás seguro?'
            )
        return value


class PendientesSerializer(serializers.Serializer):
    """
    Respuesta combinada de tareas y exámenes pendientes,
    ordenados por fecha límite más cercana.
    """
    tareas = TareaSerializer(many=True)
    examenes = ExamenSerializer(many=True)
    total_pendientes = serializers.IntegerField()
    progreso_porcentaje = serializers.FloatField()
