import requests
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta


class CanvasService:
    """
    Servicio de integración con la API de Canvas de Tecsup.
    Maneja autenticación OAuth2 e importación de tareas y exámenes.
    """

    BASE_URL = settings.CANVAS_BASE_URL

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

    def verificar_conexion(self) -> dict:
        """
        Verifica que el token es válido y obtiene datos del usuario.
        Retorna dict con id y nombre del usuario en Canvas.
        """
        try:
            response = requests.get(
                f'{self.BASE_URL}/api/v1/users/self',
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    'ok': True,
                    'canvas_user_id': str(data.get('id')),
                    'nombre': data.get('name'),
                }
            return {'ok': False, 'error': 'Token inválido o expirado'}
        except requests.exceptions.ConnectionError:
            return {'ok': False, 'error': 'No se pudo conectar con Canvas'}
        except requests.exceptions.Timeout:
            return {'ok': False, 'error': 'Canvas tardó demasiado en responder'}

    def obtener_cursos(self) -> list:
        """
        Obtiene los cursos activos del estudiante.
        """
        try:
            response = requests.get(
                f'{self.BASE_URL}/api/v1/courses',
                headers=self.headers,
                params={
                    'enrollment_state': 'active',
                    'per_page': 50,
                },
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []

    def obtener_tareas_pendientes(self) -> list:
        """
        Importa todas las tareas pendientes de los próximos 30 días.
        Devuelve lista de dicts listos para crear modelos Tarea.
        """
        tareas = []
        fecha_limite = timezone.now() + timedelta(days=30)

        try:
            # Primero obtenemos los cursos activos
            cursos = self.obtener_cursos()

            for curso in cursos:
                curso_id = curso.get('id')
                curso_nombre = curso.get('name', 'Sin nombre')

                response = requests.get(
                    f'{self.BASE_URL}/api/v1/courses/{curso_id}/assignments',
                    headers=self.headers,
                    params={
                        'bucket': 'upcoming',
                        'per_page': 100,
                        'order_by': 'due_at',
                    },
                    timeout=10
                )

                if response.status_code != 200:
                    continue

                for assignment in response.json():
                    due_at = assignment.get('due_at')
                    if not due_at:
                        continue

                    fecha_entrega = datetime.fromisoformat(
                        due_at.replace('Z', '+00:00')
                    )

                    # Solo incluir tareas en los próximos 30 días
                    if fecha_entrega <= fecha_limite:
                        tareas.append({
                            'canvas_id': str(assignment.get('id')),
                            'canvas_curso_id': str(curso_id),
                            'nombre': assignment.get('name', 'Sin nombre'),
                            'curso': curso_nombre,
                            'fecha_limite': fecha_entrega,
                            'descripcion': assignment.get('description', ''),
                            'origen': 'canvas',
                        })

        except Exception as e:
            pass

        return tareas

    def obtener_examenes_proximos(self) -> list:
        """
        Importa los exámenes (quizzes) de los próximos 30 días.
        """
        examenes = []
        fecha_limite = timezone.now() + timedelta(days=30)

        try:
            cursos = self.obtener_cursos()

            for curso in cursos:
                curso_id = curso.get('id')
                curso_nombre = curso.get('name', 'Sin nombre')

                response = requests.get(
                    f'{self.BASE_URL}/api/v1/courses/{curso_id}/quizzes',
                    headers=self.headers,
                    params={'per_page': 100},
                    timeout=10
                )

                if response.status_code != 200:
                    continue

                for quiz in response.json():
                    due_at = quiz.get('due_at') or quiz.get('lock_at')
                    if not due_at:
                        continue

                    fecha_examen = datetime.fromisoformat(
                        due_at.replace('Z', '+00:00')
                    )

                    if fecha_examen <= fecha_limite:
                        examenes.append({
                            'canvas_id': str(quiz.get('id')),
                            'canvas_curso_id': str(curso_id),
                            'curso': curso_nombre,
                            'fecha': fecha_examen,
                            'descripcion': quiz.get('title', ''),
                            'origen': 'canvas',
                        })

        except Exception:
            pass

        return examenes


def generar_url_oauth(state: str = 'examplanner') -> str:
    """
    Genera la URL de autorización OAuth2 para Canvas.
    El usuario es redirigido aquí para autorizar el acceso.
    """
    params = {
        'client_id': settings.CANVAS_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': settings.CANVAS_REDIRECT_URI,
        'scope': '/auth/userinfo /api/v1/courses /api/v1/assignments /api/v1/quizzes',
        'state': state,
    }
    query = '&'.join(f'{k}={v}' for k, v in params.items())
    return f'{settings.CANVAS_BASE_URL}/login/oauth2/auth?{query}'


def intercambiar_codigo_por_token(codigo: str) -> dict:
    """
    Intercambia el código de autorización por el access token de Canvas.
    """
    try:
        response = requests.post(
            f'{settings.CANVAS_BASE_URL}/login/oauth2/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': settings.CANVAS_CLIENT_ID,
                'client_secret': settings.CANVAS_CLIENT_SECRET,
                'redirect_uri': settings.CANVAS_REDIRECT_URI,
                'code': codigo,
            },
            timeout=15
        )
        if response.status_code == 200:
            return {'ok': True, 'token': response.json().get('access_token')}
        return {'ok': False, 'error': 'No se pudo obtener el token de Canvas'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
