from django.urls import path
from . import views

urlpatterns = [
    # API (app Android)
    path('estado/', views.EstadoSuscripcionView.as_view(), name='pagos-estado'),
    path('crear/',  views.CrearPagoView.as_view(),         name='pagos-crear'),

    # Páginas web (WebView)
    path('checkout/<int:pago_id>/', views.checkout,    name='pagos-checkout'),
    path('exitoso/',                views.pago_exitoso, name='pagos-exitoso'),
    path('fallido/',                views.pago_fallido, name='pagos-fallido'),
]
