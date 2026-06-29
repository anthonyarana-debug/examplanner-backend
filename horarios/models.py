from django.conf import settings
from django.db import models


class Horario(models.Model):
    """Una clase del horario semanal del estudiante (dato propio por cuenta)."""
    DIAS = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'), (3, 'Jueves'),
        (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo'),
    ]

    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='horarios'
    )
    curso = models.CharField(max_length=120)
    codigo = models.CharField(max_length=30, blank=True, default='')
    aula = models.CharField(max_length=30, blank=True, default='')
    dia = models.IntegerField(choices=DIAS)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        ordering = ['dia', 'hora_inicio']
        verbose_name = 'Horario'
        verbose_name_plural = 'Horarios'

    def __str__(self):
        return f'{self.curso} · {self.get_dia_display()} {self.hora_inicio:%H:%M}'
