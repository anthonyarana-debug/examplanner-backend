from django.db.models import Q

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import BloqueCurso, Asistencia
from .serializers import BloqueCursoSerializer, AsistenciaSerializer

UMBRAL = 30.0  # % de inasistencia que marca riesgo


# ── BLOQUES DE CURSO (definir cursos: Teoría/Lab + sesiones + duración) ─────────

class BloqueListCreate(generics.ListCreateAPIView):
    serializer_class = BloqueCursoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BloqueCurso.objects.filter(estudiante=self.request.user)

    def perform_create(self, serializer):
        serializer.save(estudiante=self.request.user)


class BloqueDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BloqueCursoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BloqueCurso.objects.filter(estudiante=self.request.user)


# ── REGISTRO DE ASISTENCIA (Presente / Falta por sesión) ──────────────────────

class AsistenciaListCreate(generics.ListCreateAPIView):
    serializer_class = AsistenciaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Asistencia.objects.filter(bloque__estudiante=self.request.user)

    def perform_create(self, serializer):
        # solo permite registrar en bloques propios
        bloque = serializer.validated_data['bloque']
        if bloque.estudiante_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Ese bloque no es tuyo.')
        serializer.save()


class AsistenciaDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AsistenciaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Asistencia.objects.filter(bloque__estudiante=self.request.user)


# ── RESUMEN: % de inasistencia por curso y alerta de riesgo (30%) ─────────────

class ResumenAsistenciaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bloques = BloqueCurso.objects.filter(estudiante=request.user)

        # agrupar por nombre de curso (un curso puede tener Teoría + Lab)
        cursos = {}
        for b in bloques:
            faltas = b.asistencias.filter(estado='falta').count()
            dur = float(b.duracion_sesion)
            horas_totales = dur * b.total_sesiones
            horas_falta = dur * faltas

            c = cursos.setdefault(b.curso, {
                'curso': b.curso,
                'horas_totales': 0.0,
                'horas_falta': 0.0,
                'bloques': [],
            })
            c['horas_totales'] += horas_totales
            c['horas_falta'] += horas_falta
            c['bloques'].append({
                'tipo': b.tipo,
                'faltas': faltas,
                'sesiones': b.total_sesiones,
                'duracion_sesion': dur,
                'horas_falta': round(horas_falta, 2),
            })

        resultado = []
        for c in cursos.values():
            total = c['horas_totales']
            falta = c['horas_falta']
            pct = round((falta / total * 100), 1) if total > 0 else 0.0
            # horas que aún puede faltar antes de llegar al 30%
            margen = round((total * UMBRAL / 100) - falta, 1)
            resultado.append({
                'curso': c['curso'],
                'horas_totales': round(total, 1),
                'horas_falta': round(falta, 1),
                'porcentaje_inasistencia': pct,
                'riesgo': pct >= UMBRAL,
                'horas_margen': max(margen, 0),
                'bloques': c['bloques'],
            })

        resultado.sort(key=lambda x: x['porcentaje_inasistencia'], reverse=True)
        return Response({'cursos': resultado, 'umbral': UMBRAL})
