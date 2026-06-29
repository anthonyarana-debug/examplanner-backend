from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import json
import urllib.parse

from asistente.ia_client import preguntar_ia


class RepasarView(APIView):
    """
    POST /api/repasar/
    Body: { "titulo": "...", "curso": "..." }

    Genera un plan de repaso para una tarea/examen usando la IA,
    y devuelve enlaces de BÚSQUEDA reales (no links inventados):
    YouTube, Google y Google Académico, ya armados con el tema.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        titulo = (request.data.get('titulo') or '').strip()
        curso = (request.data.get('curso') or '').strip()

        if not titulo:
            return Response(
                {'error': 'Falta el título de la tarea o examen.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Pedimos a la IA el plan en JSON estricto
        prompt = (
            f"Eres un tutor de un instituto técnico (Tecsup, Perú). "
            f"Un estudiante tiene esta evaluación/tarea:\n"
            f"- Título: {titulo}\n"
            f"- Curso: {curso}\n\n"
            f"Genera una guía de repaso breve y práctica. "
            f"Responde SOLO con un JSON válido, sin texto antes ni después, "
            f"con esta forma exacta:\n"
            f'{{"resumen": "1-2 frases sobre qué trata el tema", '
            f'"conceptos": ["concepto1", "concepto2", "concepto3", "concepto4"], '
            f'"busqueda": "frase corta ideal para buscar en YouTube/Google sobre este tema"}}\n'
            f"Todo en español. Los conceptos deben ser temas concretos para repasar."
        )

        resultado = preguntar_ia(prompt)

        if not resultado['ok']:
            return Response(
                {'error': resultado['error']},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Intentar parsear el JSON que devolvió la IA
        texto = resultado['respuesta'].strip()
        # limpiar posibles ```json ... ```
        if texto.startswith('```'):
            texto = texto.split('```')[1] if '```' in texto else texto
            if texto.startswith('json'):
                texto = texto[4:]
            texto = texto.strip()

        try:
            data = json.loads(texto)
            resumen = data.get('resumen', '')
            conceptos = data.get('conceptos', [])
            busqueda = data.get('busqueda', titulo)
        except Exception:
            # Si la IA no devolvió JSON limpio, usamos un fallback seguro
            resumen = texto[:300]
            conceptos = []
            busqueda = f"{curso} {titulo}"

        # Armar enlaces de BÚSQUEDA reales (siempre válidos, no inventados)
        q = urllib.parse.quote_plus(busqueda)
        enlaces = [
            {
                'tipo': 'YouTube',
                'descripcion': 'Videos explicativos',
                'url': f'https://www.youtube.com/results?search_query={q}',
            },
            {
                'tipo': 'Google',
                'descripcion': 'Artículos y tutoriales',
                'url': f'https://www.google.com/search?q={q}',
            },
            {
                'tipo': 'Google Académico',
                'descripcion': 'Material académico',
                'url': f'https://scholar.google.com/scholar?q={q}',
            },
        ]

        return Response({
            'titulo': titulo,
            'curso': curso,
            'resumen': resumen,
            'conceptos': conceptos,
            'busqueda': busqueda,
            'enlaces': enlaces,
        })
