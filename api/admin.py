from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Estudiante, Tarea, Examen


@admin.register(Estudiante)
class EstudianteAdmin(UserAdmin):
    list_display = ['email', 'nombre', 'canvas_conectado', 'fecha_registro']
    list_filter = ['canvas_conectado', 'is_active']
    search_fields = ['email', 'nombre']
    ordering = ['-fecha_registro']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información personal', {'fields': ('nombre',)}),
        ('Canvas', {'fields': ('canvas_conectado', 'canvas_user_id')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'password1', 'password2'),
        }),
    )


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'curso', 'estudiante', 'fecha_limite', 'completada', 'origen']
    list_filter = ['completada', 'origen', 'curso']
    search_fields = ['nombre', 'curso', 'estudiante__nombre']
    ordering = ['fecha_limite']


@admin.register(Examen)
class ExamenAdmin(admin.ModelAdmin):
    list_display = ['curso', 'estudiante', 'fecha', 'origen']
    list_filter = ['origen', 'curso']
    search_fields = ['curso', 'estudiante__nombre']
    ordering = ['fecha']
