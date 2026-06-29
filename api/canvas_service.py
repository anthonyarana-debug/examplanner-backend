import re
import requests
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta


# Palabras clave que, en un assignment normal (no quiz), indican evaluación.
PALABRAS_EXAMEN = [
    'examen',
    'evaluacion',
    'evaluación',
    'practica calificada',
    'práctica calificada',
    'parcial',
    'sustitutorio',
]


def _es_examen(nombre: str, is_quiz: bool, puntos) -> bool:
    """
    Decide si un assignment de Canvas debe tratarse como examen.

    Reglas (en orden):
      1. Si Canvas lo marca como quiz -> examen seguro.
      2. Si vale 1 punto o menos -> NO es examen (son foros / actividades
         sumativas de relleno que en Tecsup valen 1 pt).
      3. Si el nombre contiene palabras fuertes de evaluación
         (examen, evaluación, práctica calificada, PC, parcial...) -> examen.
      4. En cualquier otro caso -> tarea.
    """
    if is_quiz:
        return True

    try:
        if puntos is not None and float(puntos) <= 1:
            return False
    except (TypeError, ValueError):
        pass

    n = (nombre or '').lower()

    # 'PC' como palabra suelta o seguida de número (PC1, PC 2, PC-S05)
    if re.search(r'\bpc\s*\d', n) or re.search(r'\bpc\b', n):
        return True

    return any(palabra in n for palabra in PALABRAS_EXAMEN)


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

    def obtener_entregas(self) -> set:
        """
        Devuelve un set con los IDs (str) de assignments que el estudiante
        YA entregó o tiene calificados en Canvas. Se usa para marcar como
        completadas las tareas que ya hizo. Solo lectura.
        """
        entregados = set()
        try:
            cursos = self.obtener_cursos()
            for curso in cursos:
                curso_id = curso.get('id')
                response = requests.get(
                    f'{self.BASE_URL}/api/v1/courses/{curso_id}/students/submissions',
                    headers=self.headers,
                    params={'student_ids[]': 'self', 'per_page': 100},
                    timeout=15
                )
                if response.status_code != 200:
                    continue
                for sub in response.json():
                    if not isinstance(sub, dict):
                        continue
                    estado = sub.get('workflow_state')
                    # 'submitted' = entregado, 'graded' = calificado
                    if estado in ('submitted', 'graded') and sub.get('submitted_at'):
                        entregados.add(str(sub.get('assignment_id')))
        except Exception:
            pass
        return entregados

    def _obtener_assignments_clasificados(self) -> dict:
        """
        Recorre los assignments próximos (30 días) y los separa en:
          - 'tareas':   assignments normales
          - 'examenes': assignments que son evaluación (quiz o nombre fuerte)
        """
        tareas = []
        examenes = []
        fecha_limite = timezone.now() + timedelta(days=30)

        try:
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
                    if not isinstance(assignment, dict):
                        continue

                    due_at = assignment.get('due_at')
                    if not due_at:
                        continue

                    fecha_entrega = datetime.fromisoformat(
                        due_at.replace('Z', '+00:00')
                    )
                    if fecha_entrega > fecha_limite:
                        continue

                    nombre = assignment.get('name', 'Sin nombre')
                    is_quiz = assignment.get('is_quiz_assignment', False)
                    puntos = assignment.get('points_possible')

                    if _es_examen(nombre, is_quiz, puntos):
                        examenes.append({
                            'canvas_id': f"a{assignment.get('id')}",
                            'canvas_curso_id': str(curso_id),
                            'curso': curso_nombre,
                            'fecha': fecha_entrega,
                            'descripcion': nombre,
                            'origen': 'canvas',
                        })
                    else:
                        tareas.append({
                            'canvas_id': str(assignment.get('id')),
                            'canvas_curso_id': str(curso_id),
                            'nombre': nombre,
                            'curso': curso_nombre,
                            'fecha_limite': fecha_entrega,
                            'descripcion': assignment.get('description', ''),
                            'origen': 'canvas',
                        })

        except Exception:
            pass

        return {'tareas': tareas, 'examenes': examenes}

    def obtener_tareas_pendientes(self) -> list:
        """Devuelve solo los assignments que NO son evaluaciones."""
        return self._obtener_assignments_clasificados()['tareas']

    def obtener_examenes_proximos(self) -> list:
        """
        Devuelve los exámenes de los próximos 30 días, combinando:
          1) quizzes nativos de Canvas
          2) assignments que son evaluación (caso Tecsup)
        """
        examenes = []
        fecha_limite = timezone.now() + timedelta(days=30)

        # 1) Quizzes nativos
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
                    if not isinstance(quiz, dict):
                        continue
                    due_at = quiz.get('due_at') or quiz.get('lock_at')
                    if not due_at:
                        continue

                    fecha_examen = datetime.fromisoformat(
                        due_at.replace('Z', '+00:00')
                    )
                    if fecha_examen <= fecha_limite:
                        examenes.append({
                            'canvas_id': f"q{quiz.get('id')}",
                            'canvas_curso_id': str(curso_id),
                            'curso': curso_nombre,
                            'fecha': fecha_examen,
                            'descripcion': quiz.get('title', ''),
                            'origen': 'canvas',
                        })
        except Exception:
            pass

        # 2) Assignments que son evaluación
        try:
            examenes += self._obtener_assignments_clasificados()['examenes']
        except Exception:
            pass

        return examenes


def generar_url_oauth(state: str = 'examplanner') -> str:
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
