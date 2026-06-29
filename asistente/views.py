from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .ia_client import preguntar_ia
from .contexto import construir_contexto


class AsistenteView(APIView):
    """
    POST /api/asistente/
    Body: { "mensaje": "..." }
    Responde con el asistente IA, usando como contexto las tareas,
    exámenes y riesgos de asistencia del estudiante.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        mensaje = (request.data.get('mensaje') or '').strip()
        if not mensaje:
            return Response(
                {'error': 'Escribe una pregunta para el asistente.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contexto = construir_contexto(request.user)
        resultado = preguntar_ia(mensaje, contexto)

        if not resultado['ok']:
            return Response(
                {'error': resultado['error']},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({'respuesta': resultado['respuesta']})
