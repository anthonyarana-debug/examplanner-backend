from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/horarios/', include('horarios.urls')),
    path('api/asistencias/', include('asistencias.urls')),
    path('api/', include('asistente.urls')),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
