"""
Integración con Izipay (Smart Form / Krypton V4).
Portado del laboratorio de e-commerce, adaptado a ExamPlanner.

Flujo:
  1. crear_token_pago(): pide un formToken a Izipay con las credenciales de comercio.
  2. El frontend renderiza el formulario embebido con ese token + la public key.
  3. Al pagar, Izipay hace POST a la URL de retorno con kr-answer + kr-hash.
  4. validar_hash(): verifica que la respuesta venga realmente de Izipay.
"""
import hmac
import hashlib
import requests
from django.conf import settings


def crear_token_pago(amount_cents: int, order_id: str, email: str, nombre: str):
    """
    Solicita un formToken a Izipay. Devuelve el token (str) o None si falla.
    amount_cents: monto en céntimos (ej. 990 = S/ 9.90)
    """
    payload = {
        "amount": amount_cents,
        "currency": "PEN",
        "orderId": order_id,
        "customer": {
            "email": email,
            "billingDetails": {"firstName": nombre},
        },
    }
    try:
        response = requests.post(
            settings.IZIPAY_API_URL,
            json=payload,
            auth=(settings.IZIPAY_SHOP_ID, settings.IZIPAY_API_KEY),
            timeout=15,
        )
        data = response.json()
        if data.get("status") == "SUCCESS":
            return data["answer"]["formToken"]
    except Exception:
        pass
    return None



def validar_hash(kr_answer_raw, kr_hash, kr_hash_key='sha256_hmac'):
    if not kr_answer_raw or not kr_hash:
        return False
    if kr_hash_key == 'password':
        clave = settings.IZIPAY_API_KEY
    else:  # 'sha256_hmac' — caso del retorno al navegador
        clave = getattr(settings, 'IZIPAY_HMAC_KEY', '')
    if not clave:
        return False
    calculado = hmac.new(clave.encode('utf-8'),
                         kr_answer_raw.encode('utf-8'),
                         hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculado, kr_hash)
