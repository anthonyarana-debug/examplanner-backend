"""
Arma un resumen del estado académico del estudiante para dárselo a la IA.
Reutiliza los modelos existentes sin acoplarse fuerte: usa imports perezosos
y try/except para que el asistente funcione aunque falte algún módulo.
"""
from django.utils import timezone
from datetime import timedelta


def construir_contexto(estudiante) -> str:
    partes = []

    # ----- Tareas pendientes -----
    try:
        from api.models import Tarea
        limite = timezone.now() + timedelta(days=14)
        tareas = Tarea.objects.filter(
            estudiante=estudiante,
            completada=False,
            fecha_limite__lte=limite,
        ).order_by('fecha_limite')[:8]
        if tareas:
            lineas = [
                f"- {t.nombre} ({t.curso}) vence {t.fecha_limite.strftime('%d/%m')}"
                for t in tareas
            ]
            partes.append("Tareas pendientes (14 días):\n" + "\n".join(lineas))
    except Exception:
        pass

    # ----- Exámenes próximos -----
    try:
        from api.models import Examen
        examenes = Examen.objects.filter(
            estudiante=estudiante,
            fecha__gte=timezone.now(),
        ).order_by('fecha')[:6]
        if examenes:
            lineas = [
                f"- {e.curso}: {(e.descripcion or 'Examen')} el {e.fecha.strftime('%d/%m')}"
                for e in examenes
            ]
            partes.append("Exámenes próximos:\n" + "\n".join(lineas))
    except Exception:
        pass

    # ----- Riesgo de asistencia -----
    try:
        from asistencias.models import BloqueCurso, Asistencia
        bloques = BloqueCurso.objects.filter(estudiante=estudiante)
        riesgos = []
        for b in bloques:
            faltas = Asistencia.objects.filter(bloque=b, estado='falta').count()
            horas_falta = faltas * float(b.duracion_sesion)
            horas_totales = b.horas_totales
            if horas_totales > 0:
                pct = horas_falta / horas_totales * 100
                if pct >= 20:
                    riesgos.append(
                        f"- {b.curso} ({b.tipo}): {pct:.0f}% de inasistencia"
                    )
        if riesgos:
            partes.append("Cursos con riesgo de asistencia:\n" + "\n".join(riesgos))
    except Exception:
        pass

    if not partes:
        return "El estudiante no tiene tareas, exámenes ni riesgos registrados por ahora."

    return "\n\n".join(partes)
