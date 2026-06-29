from django.contrib import admin
from .models import BloqueCurso, Asistencia


@admin.register(BloqueCurso)
class BloqueCursoAdmin(admin.ModelAdmin):
    list_display = ('curso', 'tipo', 'total_sesiones', 'duracion_sesion', 'horas_totales', 'estudiante')
    search_fields = ('curso', 'estudiante__email')


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('bloque', 'fecha', 'estado')
    list_filter = ('estado',)
