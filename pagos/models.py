from django.conf import settings
from django.db import models
from django.utils import timezone


class Pago(models.Model):
    """
    Representa un intento de pago de la suscripción ExamPlanner Pro.
    Desacoplado del resto del sistema: vive en su propia app `pagos`.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('fallido', 'Fallido'),
    ]

    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pagos'
    )
    plan = models.CharField(max_length=30, default='pro')
    orden_id = models.CharField(max_length=80, unique=True)
    monto_centavos = models.IntegerField()
    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default='pendiente')
    form_token = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_pago = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'

    def __str__(self):
        return f'{self.orden_id} — {self.estudiante.email} — {self.estado}'

    @property
    def monto_soles(self):
        return self.monto_centavos / 100


def estudiante_es_pro(estudiante) -> bool:
    """Un estudiante es Pro si tiene al menos un pago confirmado."""
    return Pago.objects.filter(estudiante=estudiante, estado='pagado').exists()
