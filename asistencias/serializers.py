from rest_framework import serializers
from .models import BloqueCurso, Asistencia


class BloqueCursoSerializer(serializers.ModelSerializer):
    horas_totales = serializers.FloatField(read_only=True)

    class Meta:
        model = BloqueCurso
        fields = ['id', 'curso', 'tipo', 'total_sesiones', 'duracion_sesion', 'horas_totales']

    def validate_total_sesiones(self, v):
        if v <= 0:
            raise serializers.ValidationError('Debe ser mayor que 0.')
        return v


class AsistenciaSerializer(serializers.ModelSerializer):
    curso = serializers.CharField(source='bloque.curso', read_only=True)
    tipo = serializers.CharField(source='bloque.tipo', read_only=True)

    class Meta:
        model = Asistencia
        fields = ['id', 'bloque', 'curso', 'tipo', 'fecha', 'estado']
