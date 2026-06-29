from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

from .models import Estudiante, Tarea, Examen
from .serializers import (
    RegistroSerializer, LoginSerializer, EstudianteSerializer,
    TareaSerializer, ExamenSerializer, PendientesSerializer
)
from .canvas_service import (
    CanvasService, generar_url_oauth, intercambiar_codigo_por_token
)


def get_tokens_for_user(estudiante):
    """Genera par de tokens JWT para el estudiante."""
    refresh = RefreshToken.for_user(estudiante)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# ─── AUTENTICACIÓN ────────────────────────────────────────────────────────────

class RegistroView(APIView):
    """
    POST /api/auth/registro/
    Crea una cuenta nueva con correo @tecsup.edu.pe.

    Body: { email, nombre, password, password_confirmacion }

    CA1: Si el correo no termina en @tecsup.edu.pe → 400
    CA2: Si todo es correcto → 201 con tokens y datos del estudiante
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistroSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errores': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        estudiante = serializer.save()
        tokens = get_tokens_for_user(estudiante)
        return Response(
            {
                'mensaje': 'Cuenta creada exitosamente',
                'estudiante': EstudianteSerializer(estudiante).data,
                'tokens': tokens,
            },
            status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    """
    POST /api/auth/login/
    Inicia sesión y devuelve tokens JWT.

    Body: { email, password }

    CA1: Credenciales incorrectas → 401 sin especificar cuál es el error
    CA2: Credenciales correctas → 200 con tokens y datos del estudiante
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Usuario o contraseña incorrectos'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        estudiante = serializer.validated_data['estudiante']
        tokens = get_tokens_for_user(estudiante)
        return Response(
            {
                'mensaje': f'Bienvenido, {estudiante.nombre}',
                'estudiante': EstudianteSerializer(estudiante).data,
                'tokens': tokens,
            },
            status=status.HTTP_200_OK
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Invalida el refresh token del estudiante.

    Body: { refresh }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {'mensaje': 'Sesión cerrada correctamente'},
                status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {'error': 'Token inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )


# ─── CANVAS ───────────────────────────────────────────────────────────────────

class CanvasOAuthView(APIView):
    """
    GET /api/canvas/autorizar/
    Devuelve la URL para que el estudiante autorice ExamPlanner en Canvas.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        url = generar_url_oauth(state=str(request.user.id))
        return Response({'url_autorizacion': url})


class CanvasCallbackView(APIView):
    """
    GET /api/canvas/callback/?code=xxx
    Canvas redirige aquí con el código de autorización.
    Intercambia el código por el token, importa tareas y exámenes.

    CA1: Conexión exitosa → importa tareas de los próximos 30 días
    CA2: Canvas no disponible o acceso rechazado → habilita registro manual
    """
    permission_classes = [AllowAny]

    def get(self, request):
        codigo = request.query_params.get('code')
        state = request.query_params.get('state')  # ID del estudiante

        if not codigo:
            return Response(
                {
                    'error': 'No se pudo conectar con Canvas. Puedes agregar tus tareas manualmente.',
                    'registro_manual_habilitado': True,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        resultado = intercambiar_codigo_por_token(codigo)
        if not resultado['ok']:
            return Response(
                {
                    'error': 'No se pudo conectar con Canvas. Puedes agregar tus tareas manualmente.',
                    'registro_manual_habilitado': True,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        token = resultado['token']

        # Obtener el estudiante por el state (su ID)
        try:
            estudiante = Estudiante.objects.get(id=state)
        except Estudiante.DoesNotExist:
            return Response({'error': 'Estudiante no encontrado'}, status=404)

        # Verificar el token con Canvas
        servicio = CanvasService(token)
        verificacion = servicio.verificar_conexion()

        if not verificacion['ok']:
            return Response(
                {
                    'error': 'No se pudo conectar con Canvas. Puedes agregar tus tareas manualmente.',
                    'registro_manual_habilitado': True,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Guardar token y marcar canvas como conectado
        estudiante.canvas_token = token
        estudiante.canvas_user_id = verificacion['canvas_user_id']
        estudiante.canvas_conectado = True
        estudiante.save()

        # Importar tareas y exámenes
        tareas_importadas = _importar_tareas_canvas(estudiante, servicio)
        examenes_importados = _importar_examenes_canvas(estudiante, servicio)

        return Response(
            {
                'mensaje': 'Canvas conectado exitosamente',
                'tareas_importadas': tareas_importadas,
                'examenes_importados': examenes_importados,
            },
            status=status.HTTP_200_OK
        )


class CanvasConectarTokenView(APIView):
    """
    POST /api/canvas/conectar/
    Alternativa para conectar Canvas usando un token personal
    (útil para desarrollo y pruebas sin OAuth completo).

    Body: { token }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response(
                {'error': 'Token de Canvas requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        servicio = CanvasService(token)
        verificacion = servicio.verificar_conexion()

        if not verificacion['ok']:
            return Response(
                {
                    'error': 'No se pudo conectar con Canvas. Puedes agregar tus tareas manualmente.',
                    'registro_manual_habilitado': True,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        estudiante = request.user
        estudiante.canvas_token = token
        estudiante.canvas_user_id = verificacion['canvas_user_id']
        estudiante.canvas_conectado = True
        estudiante.save()

        tareas_importadas = _importar_tareas_canvas(estudiante, servicio)
        examenes_importados = _importar_examenes_canvas(estudiante, servicio)

        return Response(
            {
                'mensaje': f'Canvas conectado. Bienvenido {verificacion["nombre"]}',
                'tareas_importadas': tareas_importadas,
                'examenes_importados': examenes_importados,
            },
            status=status.HTTP_200_OK
        )


class CanvasSincronizarView(APIView):
    """
    POST /api/canvas/sincronizar/
    Re-importa tareas y exámenes de Canvas sin desconectar.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        estudiante = request.user
        if not estudiante.canvas_conectado or not estudiante.canvas_token:
            return Response(
                {'error': 'Canvas no está conectado'},
                status=status.HTTP_400_BAD_REQUEST
            )

        servicio = CanvasService(estudiante.canvas_token)
        tareas_importadas = _importar_tareas_canvas(estudiante, servicio)
        examenes_importados = _importar_examenes_canvas(estudiante, servicio)

        return Response(
            {
                'mensaje': 'Sincronización completada',
                'tareas_importadas': tareas_importadas,
                'examenes_importados': examenes_importados,
            }
        )


# ─── TAREAS ───────────────────────────────────────────────────────────────────

class PendientesView(APIView):
    """
    GET /api/pendientes/
    Lista todas las tareas y exámenes pendientes del estudiante,
    ordenados por fecha límite más cercana.

    CA1: Hay pendientes → lista ordenada con nombre del curso y días restantes
    CA2: No hay pendientes y Canvas no conectado → mensaje orientador
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        estudiante = request.user

        tareas = Tarea.objects.filter(
            estudiante=estudiante,
            completada=False
        ).order_by('fecha_limite')

        examenes = Examen.objects.filter(
            estudiante=estudiante,
            fecha__gte=timezone.now()
        ).order_by('fecha')

        total_tareas = Tarea.objects.filter(estudiante=estudiante).count()
        tareas_completadas = Tarea.objects.filter(
            estudiante=estudiante, completada=True
        ).count()

        if total_tareas > 0:
            progreso = (tareas_completadas / total_tareas) * 100
        else:
            progreso = 0

        if not tareas.exists() and not examenes.exists():
            mensaje = (
                'No tienes tareas registradas. Conecta Canvas o agrega una manualmente.'
                if not estudiante.canvas_conectado
                else 'No tienes pendientes por ahora. ¡Bien hecho!'
            )
            return Response(
                {
                    'tareas': [],
                    'examenes': [],
                    'total_pendientes': 0,
                    'progreso_porcentaje': progreso,
                    'mensaje': mensaje,
                    'canvas_conectado': estudiante.canvas_conectado,
                }
            )

        return Response(
            {
                'tareas': TareaSerializer(tareas, many=True).data,
                'examenes': ExamenSerializer(examenes, many=True).data,
                'total_pendientes': tareas.count() + examenes.count(),
                'progreso_porcentaje': round(progreso, 1),
                'canvas_conectado': estudiante.canvas_conectado,
            }
        )


class TareaListCreateView(APIView):
    """
    GET  /api/tareas/        → lista todas las tareas del estudiante
    POST /api/tareas/        → crea una tarea manual
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tareas = Tarea.objects.filter(
            estudiante=request.user
        ).order_by('fecha_limite')
        return Response(TareaSerializer(tareas, many=True).data)

    def post(self, request):
        serializer = TareaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        tarea = serializer.save(
            estudiante=request.user,
            origen='manual'
        )
        return Response(
            TareaSerializer(tarea).data,
            status=status.HTTP_201_CREATED
        )


class TareaDetailView(APIView):
    """
    GET    /api/tareas/<id>/   → detalle de una tarea
    PUT    /api/tareas/<id>/   → edita nombre, curso o fecha
    DELETE /api/tareas/<id>/   → elimina la tarea
    """
    permission_classes = [IsAuthenticated]

    def _get_tarea(self, pk, estudiante):
        try:
            return Tarea.objects.get(pk=pk, estudiante=estudiante)
        except Tarea.DoesNotExist:
            return None

    def get(self, request, pk):
        tarea = self._get_tarea(pk, request.user)
        if not tarea:
            return Response({'error': 'Tarea no encontrada'}, status=404)
        return Response(TareaSerializer(tarea).data)

    def put(self, request, pk):
        tarea = self._get_tarea(pk, request.user)
        if not tarea:
            return Response({'error': 'Tarea no encontrada'}, status=404)
        serializer = TareaSerializer(tarea, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        tarea = self._get_tarea(pk, request.user)
        if not tarea:
            return Response({'error': 'Tarea no encontrada'}, status=404)
        tarea.delete()
        return Response(
            {'mensaje': 'Tarea eliminada correctamente'},
            status=status.HTTP_204_NO_CONTENT
        )


class TareaCompletarView(APIView):
    """
    PATCH /api/tareas/<id>/completar/
    Marca o desmarca una tarea como completada.

    CA1: Marcar → cambia estado, guarda fecha, actualiza progreso
    CA2: Desmarcar (completada=False) → vuelve a pendiente
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            tarea = Tarea.objects.get(pk=pk, estudiante=request.user)
        except Tarea.DoesNotExist:
            return Response({'error': 'Tarea no encontrada'}, status=404)

        completada = request.data.get('completada', True)
        tarea.completada = completada
        tarea.fecha_completada = timezone.now() if completada else None
        tarea.save()

        return Response(
            {
                'mensaje': 'Tarea completada' if completada else 'Tarea marcada como pendiente',
                'tarea': TareaSerializer(tarea).data,
            }
        )


# ─── EXÁMENES ─────────────────────────────────────────────────────────────────

class ExamenListCreateView(APIView):
    """
    GET  /api/examenes/   → lista exámenes del estudiante
    POST /api/examenes/   → registra examen manual
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        examenes = Examen.objects.filter(
            estudiante=request.user,
            fecha__gte=timezone.now()
        ).order_by('fecha')
        return Response(ExamenSerializer(examenes, many=True).data)

    def post(self, request):
        serializer = ExamenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        examen = serializer.save(
            estudiante=request.user,
            origen='manual'
        )
        return Response(
            ExamenSerializer(examen).data,
            status=status.HTTP_201_CREATED
        )


# ─── HELPERS INTERNOS ─────────────────────────────────────────────────────────

def _importar_tareas_canvas(estudiante, servicio: CanvasService) -> int:
    """
    Importa tareas desde Canvas. Si ya existe una con el mismo canvas_id
    no la duplica, solo la actualiza. Además, si la tarea ya figura como
    ENTREGADA o CALIFICADA en Canvas, la marca como completada en la app.
    """
    from django.utils import timezone

    tareas_data = servicio.obtener_tareas_pendientes()
    entregados = servicio.obtener_entregas()
    importadas = 0

    for data in tareas_data:
        canvas_id = data['canvas_id']
        ya_entregada = canvas_id in entregados

        tarea, creada = Tarea.objects.update_or_create(
            estudiante=estudiante,
            canvas_id=canvas_id,
            defaults={
                'nombre': data['nombre'],
                'curso': data['curso'],
                'fecha_limite': data['fecha_limite'],
                'descripcion': data.get('descripcion', ''),
                'canvas_curso_id': data.get('canvas_curso_id', ''),
                'origen': 'canvas',
            }
        )

        if ya_entregada and not tarea.completada:
            tarea.completada = True
            tarea.fecha_completada = timezone.now()
            tarea.save()

        if creada:
            importadas += 1

    return importadas


def _importar_examenes_canvas(estudiante, servicio: CanvasService) -> int:
    """
    Importa exámenes desde Canvas sin duplicar.
    """
    examenes_data = servicio.obtener_examenes_proximos()
    importados = 0

    for data in examenes_data:
        examen, creado = Examen.objects.update_or_create(
            estudiante=estudiante,
            canvas_id=data['canvas_id'],
            defaults={
                'curso': data['curso'],
                'fecha': data['fecha'],
                'descripcion': data.get('descripcion', ''),
                'canvas_curso_id': data.get('canvas_curso_id', ''),
                'origen': 'canvas',
            }
        )
        if creado:
            importados += 1

    return importados
