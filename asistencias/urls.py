from django.urls import path
from . import views

urlpatterns = [
    # resumen / alerta de riesgo
    path('resumen/', views.ResumenAsistenciaView.as_view(), name='asistencia-resumen'),

    # bloques de curso (Teoría/Lab + sesiones + duración)
    path('bloques/', views.BloqueListCreate.as_view(), name='bloque-list'),
    path('bloques/<int:pk>/', views.BloqueDetail.as_view(), name='bloque-detail'),

    # registros de asistencia (Presente/Falta por sesión)
    path('', views.AsistenciaListCreate.as_view(), name='asistencia-list'),
    path('<int:pk>/', views.AsistenciaDetail.as_view(), name='asistencia-detail'),
]
