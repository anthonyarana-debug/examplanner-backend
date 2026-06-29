from django.contrib import admin
from .models import Horario


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ('curso', 'codigo', 'aula', 'get_dia_display', 'hora_inicio', 'hora_fin', 'estudiante')
    list_filter = ('dia',)
    search_fields = ('curso', 'codigo', 'estudiante__email')
