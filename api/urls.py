from django.urls import path
from .canvas_academico import NotasView, AnunciosView, MaterialesView
from . import views

urlpatterns = [
    # Autenticación
    path('auth/registro/',       views.RegistroView.as_view(),       name='registro'),
    path('auth/login/',          views.LoginView.as_view(),          name='login'),
    path('auth/logout/',         views.LogoutView.as_view(),         name='logout'),

    # Canvas
    path('canvas/materiales/', MaterialesView.as_view(), name='canvas-materiales'),
    path('canvas/notas/',    NotasView.as_view(),    name='canvas-notas'),
    path('canvas/anuncios/', AnunciosView.as_view(), name='canvas-anuncios'),
    path('canvas/autorizar/',    views.CanvasOAuthView.as_view(),    name='canvas-autorizar'),
    path('canvas/callback/',     views.CanvasCallbackView.as_view(), name='canvas-callback'),
    path('canvas/conectar/',     views.CanvasConectarTokenView.as_view(), name='canvas-conectar'),
    path('canvas/sincronizar/',  views.CanvasSincronizarView.as_view(), name='canvas-sincronizar'),

    # Pendientes (tareas + exámenes combinados)
    path('pendientes/',          views.PendientesView.as_view(),     name='pendientes'),

    # Tareas
    path('tareas/',              views.TareaListCreateView.as_view(),  name='tareas-list'),
    path('tareas/<int:pk>/',     views.TareaDetailView.as_view(),      name='tareas-detail'),
    path('tareas/<int:pk>/completar/', views.TareaCompletarView.as_view(), name='tareas-completar'),

    # Exámenes
    path('examenes/',            views.ExamenListCreateView.as_view(), name='examenes-list'),
]
