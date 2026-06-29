from rest_framework import serializers
from .models import Horario


class HorarioSerializer(serializers.ModelSerializer):
    dia_nombre = serializers.CharField(source='get_dia_display', read_only=True)

    class Meta:
        model = Horario
        fields = [
            'id', 'curso', 'codigo', 'aula',
            'dia', 'dia_nombre', 'hora_inicio', 'hora_fin',
        ]

    def validate(self, data):
        ini = data.get('hora_inicio')
        fin = data.get('hora_fin')
        if ini and fin and fin <= ini:
            raise serializers.ValidationError(
                'La hora de fin debe ser mayor que la de inicio.'
            )
        return data
