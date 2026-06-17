from django.contrib import admin
from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('orden_id', 'estudiante', 'plan', 'monto_soles', 'estado', 'fecha_creacion', 'fecha_pago')
    list_filter = ('estado', 'plan')
    search_fields = ('orden_id', 'estudiante__email')
    readonly_fields = ('form_token', 'fecha_creacion', 'fecha_pago')
