from django.urls import path
from .views import AsistenteView
from .views_repasar import RepasarView

urlpatterns = [
    path('asistente/', AsistenteView.as_view(), name='asistente'),
    path('repasar/', RepasarView.as_view(), name='repasar'),
]
