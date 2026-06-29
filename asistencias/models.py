from django.conf import settings
from django.db import models


class BloqueCurso(models.Model):
    """
    Un bloque de un curso (Teoría, Laboratorio, Taller, etc.).
    Un curso puede tener 1 o 2 bloques, cada uno con su duración y nº de sesiones.
    horas_totales = total_sesiones * duracion_sesion
    """
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bloques_curso'
    )
    curso = models.CharField(max_length=120)
    tipo = models.CharField(max_length=40, default='Teoría')  # texto libre
    total_sesiones = models.IntegerField()
    duracion_sesion = models.DecimalField(max_digits=4, decimal_places=2)  # horas

    class Meta:
        ordering = ['curso', 'tipo']
        verbose_name = 'Bloque de curso'
        verbose_name_plural = 'Bloques de curso'

    def __str__(self):
        return f'{self.curso} · {self.tipo}'

    @property
    def horas_totales(self):
        return float(self.duracion_sesion) * self.total_sesiones


class Asistencia(models.Model):
    """Un registro por sesión: Presente o Falta (sistema binario, sin tardanzas)."""
    ESTADOS = [
        ('presente', 'Presente'),
        ('falta', 'Falta'),
    ]
    bloque = models.ForeignKey(
        BloqueCurso, on_delete=models.CASCADE, related_name='asistencias'
    )
    fecha = models.DateField()
    estado = models.CharField(max_length=10, choices=ESTADOS, default='presente')

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'

    def __str__(self):
        return f'{self.bloque} · {self.fecha} · {self.estado}'
