from datetime import timedelta

from django.utils import timezone

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Horario
from .serializers import HorarioSerializer


class HorarioListCreate(generics.ListCreateAPIView):
    """GET lista mis clases · POST crea una clase."""
    serializer_class = HorarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Horario.objects.filter(estudiante=self.request.user)

    def perform_create(self, serializer):
        serializer.save(estudiante=self.request.user)


class HorarioDetail(generics.RetrieveUpdateDestroyAPIView):
    """GET / PUT / PATCH / DELETE de una clase propia."""
    serializer_class = HorarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Horario.objects.filter(estudiante=self.request.user)


class ProximaClaseView(APIView):
    """GET /api/horarios/proxima/ — la clase en curso o la siguiente."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # America/Lima = UTC-5 (sin horario de verano)
        ahora = timezone.now() - timedelta(hours=5)
        hoy = ahora.weekday()                       # 0=Lunes ... 6=Domingo
        ahora_min = ahora.hour * 60 + ahora.minute

        horarios = list(Horario.objects.filter(estudiante=request.user))
        if not horarios:
            return Response({'en_curso': False, 'clase': None})

        # ¿Hay una clase en curso ahora mismo?
        for h in horarios:
            if h.dia == hoy:
                ini = h.hora_inicio.hour * 60 + h.hora_inicio.minute
                fin = h.hora_fin.hour * 60 + h.hora_fin.minute
                if ini <= ahora_min <= fin:
                    return Response({
                        'en_curso': True,
                        'clase': HorarioSerializer(h).data,
                    })

        # Si no, la próxima en la semana (cíclico)
        mejor = None
        mejor_delta = None
        for h in horarios:
            ini = h.hora_inicio.hour * 60 + h.hora_inicio.minute
            dias_adelante = (h.dia - hoy) % 7
            delta = dias_adelante * 1440 + (ini - ahora_min)
            if delta < 0:
                delta += 7 * 1440
            if mejor_delta is None or delta < mejor_delta:
                mejor_delta = delta
                mejor = h

        return Response({
            'en_curso': False,
            'minutos_para_inicio': mejor_delta,
            'clase': HorarioSerializer(mejor).data,
        })
