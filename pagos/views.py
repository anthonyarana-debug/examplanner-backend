import json
import uuid

from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Pago, estudiante_es_pro
from .izipay import crear_token_pago, validar_hash

# Precio de la suscripción ExamPlanner Pro (en céntimos): S/ 9.90
PLAN_PRO_CENTAVOS = 990


# ─── API (consumida por la app Android) ───────────────────────────────────────

class EstadoSuscripcionView(APIView):
    """
    GET /api/pagos/estado/
    Indica si el estudiante ya tiene ExamPlanner Pro activo.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'es_pro': estudiante_es_pro(request.user),
            'plan': 'pro',
            'precio': '9.90',
            'moneda': 'PEN',
        })


class CrearPagoView(APIView):
    """
    POST /api/pagos/crear/
    Crea un intento de pago, pide el formToken a Izipay y devuelve la URL
    de checkout que la app abrirá en un WebView.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        estudiante = request.user

        if estudiante_es_pro(estudiante):
            return Response(
                {'error': 'Ya tienes ExamPlanner Pro activo'},
                status=status.HTTP_400_BAD_REQUEST
            )

        orden_id = f'EP-{estudiante.id}-{uuid.uuid4().hex[:8]}'
        token = crear_token_pago(
            amount_cents=PLAN_PRO_CENTAVOS,
            order_id=orden_id,
            email=estudiante.email,
            nombre=estudiante.nombre,
        )

        if not token:
            return Response(
                {'error': 'No se pudo iniciar el pago con Izipay. Intenta de nuevo.'},
                status=status.HTTP_502_BAD_GATEWAY
            )

        pago = Pago.objects.create(
            estudiante=estudiante,
            orden_id=orden_id,
            monto_centavos=PLAN_PRO_CENTAVOS,
            form_token=token,
            estado='pendiente',
        )

        checkout_url = request.build_absolute_uri(f'/api/pagos/checkout/{pago.id}/')
        return Response({
            'pago_id': pago.id,
            'orden_id': orden_id,
            'monto': '9.90',
            'checkout_url': checkout_url,
        }, status=status.HTTP_201_CREATED)


# ─── Páginas web (cargadas dentro del WebView) ────────────────────────────────

def checkout(request, pago_id):
    """
    GET /api/pagos/checkout/<id>/
    Sirve el formulario embebido de Izipay. Se abre en el WebView de la app.
    """
    pago = get_object_or_404(Pago, id=pago_id)
    return render(request, 'pagos/checkout_pro.html', {
        'form_token': pago.form_token,
        'public_key': settings.IZIPAY_PUBLIC_KEY,
        'pago': pago,
    })


@csrf_exempt
def pago_exitoso(request):
    """
    POST /api/pagos/exitoso/
    Izipay redirige aquí tras un pago aprobado. Validamos la firma y
    marcamos el pago como pagado. La app detecta esta URL en el WebView.
    """
    ok = False
    kr_answer = request.POST.get('kr-answer')
    kr_hash = request.POST.get('kr-hash')

    kr_hash_key = request.POST.get('kr-hash-key', 'sha256_hmac')
    if validar_hash(kr_answer, kr_hash, kr_hash_key):
        try:
            data = json.loads(kr_answer)
            orden_id = data.get('orderDetails', {}).get('orderId')
            pago = Pago.objects.get(orden_id=orden_id)
            if pago.estado != 'pagado':
                pago.estado = 'pagado'
                pago.fecha_pago = timezone.now()
                pago.save()
            ok = True
        except (Pago.DoesNotExist, json.JSONDecodeError, AttributeError):
            ok = False

    return render(request, 'pagos/resultado.html', {'ok': ok})


@csrf_exempt
def pago_fallido(request):
    """
    POST /api/pagos/fallido/
    Izipay redirige aquí si el pago fue rechazado.
    """
    kr_answer = request.POST.get('kr-answer')
    try:
        data = json.loads(kr_answer) if kr_answer else {}
        orden_id = data.get('orderDetails', {}).get('orderId')
        if orden_id:
            Pago.objects.filter(orden_id=orden_id).update(estado='fallido')
    except json.JSONDecodeError:
        pass
    return render(request, 'pagos/resultado.html', {'ok': False})
