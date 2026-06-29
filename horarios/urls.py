from django.urls import path
from . import views

urlpatterns = [
    path('', views.HorarioListCreate.as_view(), name='horario-list'),
    path('proxima/', views.ProximaClaseView.as_view(), name='horario-proxima'),
    path('<int:pk>/', views.HorarioDetail.as_view(), name='horario-detail'),
]
