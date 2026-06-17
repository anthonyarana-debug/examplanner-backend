"""
Endpoints académicos que leen datos en vivo desde Canvas:
  - Notas y promedio general
  - Anuncios de los cursos (texto limpio, sin HTML)
Se apoyan en el canvas_token que el estudiante ya guardó al conectar Canvas.
"""
import re
import html as html_mod
import requests
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

CANVAS_BASE_URL = settings.CANVAS_BASE_URL


def _headers(token):
    return {'Authorization': f'Bearer {token}'}


def _nombre_corto(nombre):
    """Recorta el ruido de seccion del nombre del curso de Canvas."""
    if not nombre:
        return 'Sin nombre'
    return nombre.split(' - C24')[0].strip()


def _limpiar_html(texto):
    """Convierte el HTML de un anuncio en texto plano legible."""
    if not texto:
        return ''
    # quitar bloques script/style/link completos
    texto = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', texto)
    texto = re.sub(r'(?is)<link[^>]*>', ' ', texto)
    # quitar el resto de etiquetas
    texto = re.sub(r'(?s)<[^>]+>', ' ', texto)
    texto = html_mod.unescape(texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto[:400]


def _cursos_activos(token):
    """Cursos activos del estudiante con sus notas (total_scores)."""
    try:
        r = requests.get(
            f'{CANVAS_BASE_URL}/api/v1/courses',
            headers=_headers(token),
            params={
                'enrollment_state': 'active',
                'include[]': 'total_scores',
                'per_page': 50,
            },
            timeout=15,
        )
        if r.status_code == 200:
            return [c for c in r.json() if isinstance(c, dict)]
    except Exception:
        pass
    return []


class NotasView(APIView):
    """
    GET /api/canvas/notas/
    Devuelve la nota actual de cada curso y el promedio general.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        est = request.user
        if not est.canvas_conectado or not est.canvas_token:
            return Response(
                {'error': 'Canvas no está conectado', 'notas': [], 'promedio_general': None},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cursos = _cursos_activos(est.canvas_token)
        notas = []
        suma = 0
        cuenta = 0

        for c in cursos:
            enrollments = c.get('enrollments') or []
            score = None
            letra = None
            for e in enrollments:
                if e.get('type') == 'student':
                    score = e.get('computed_current_score')
                    letra = e.get('computed_current_grade')
                    break
            notas.append({
                'curso': _nombre_corto(c.get('name')),
                'nota_actual': score,
                'nota_letra': letra,
            })
            if score is not None:
                suma += score
                cuenta += 1

        promedio = round(suma / cuenta, 2) if cuenta else None

        return Response({
            'notas': notas,
            'promedio_general': promedio,
            'total_cursos': len(notas),
        })


class AnunciosView(APIView):
    """
    GET /api/canvas/anuncios/
    Devuelve los anuncios recientes de todos los cursos activos (texto limpio).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        est = request.user
        if not est.canvas_conectado or not est.canvas_token:
            return Response(
                {'error': 'Canvas no está conectado', 'anuncios': []},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cursos = _cursos_activos(est.canvas_token)
        nombres = {c.get('id'): _nombre_corto(c.get('name')) for c in cursos}
        context_codes = [f"course_{c.get('id')}" for c in cursos if c.get('id')]

        anuncios = []
        if context_codes:
            inicio = (timezone.now() - timedelta(days=120)).strftime('%Y-%m-%d')
            params = [('context_codes[]', cc) for cc in context_codes]
            params += [('start_date', inicio), ('per_page', '40'), ('active_only', 'true')]
            try:
                r = requests.get(
                    f'{CANVAS_BASE_URL}/api/v1/announcements',
                    headers=_headers(est.canvas_token),
                    params=params,
                    timeout=15,
                )
                if r.status_code == 200:
                    for a in r.json():
                        if not isinstance(a, dict):
                            continue
                        cc = a.get('context_code', '')
                        cid = int(cc.split('_')[1]) if '_' in cc else None
                        anuncios.append({
                            'titulo': a.get('title', '(sin título)'),
                            'curso': nombres.get(cid, 'Curso'),
                            'fecha': a.get('posted_at'),
                            'mensaje': _limpiar_html(a.get('message')),
                            'url': a.get('html_url'),
                        })
            except Exception:
                pass

        # recientes primero (los que tienen fecha), luego el resto
        anuncios.sort(key=lambda x: x['fecha'] or '', reverse=True)
        return Response({'anuncios': anuncios, 'total': len(anuncios)})
