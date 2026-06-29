"""
Cliente de IA para el asistente de ExamPlanner.
Usa un endpoint compatible con OpenAI (por defecto Groq) configurable por .env:
  IA_API_KEY   -> clave del proveedor (obligatoria)
  IA_BASE_URL  -> base URL del endpoint (default Groq)
  IA_MODEL     -> modelo a usar (default llama-3.3-70b-versatile)
Cambiar de proveedor (OpenAI, Gemini-OpenAI, etc.) es solo cambiar estas 3 vars.
"""
import requests
from django.conf import settings


def preguntar_ia(mensaje_usuario: str, contexto: str = "") -> dict:
    api_key = getattr(settings, 'IA_API_KEY', '')
    base_url = getattr(settings, 'IA_BASE_URL', 'https://api.groq.com/openai/v1')
    modelo = getattr(settings, 'IA_MODEL', 'llama-3.3-70b-versatile')

    if not api_key:
        return {'ok': False, 'error': 'El asistente no está configurado todavía.'}

    system_prompt = (
        "Eres el asistente académico de ExamPlanner, una app para estudiantes "
        "de Tecsup (instituto técnico en Perú). Ayudas a organizar tareas, "
        "exámenes, horarios y a no descuidar la asistencia. Responde en español, "
        "de forma breve, concreta y motivadora. Da pasos prácticos y realistas. "
        "Si el estudiante tiene riesgo de inasistencia o entregas próximas, "
        "priorízalo en tu respuesta. No inventes datos que no estén en el contexto."
    )

    if contexto:
        system_prompt += f"\n\nContexto actual del estudiante:\n{contexto}"

    try:
        response = requests.post(
            f'{base_url}/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': modelo,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': mensaje_usuario},
                ],
                'temperature': 0.7,
                'max_tokens': 600,
            },
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            texto = data['choices'][0]['message']['content']
            return {'ok': True, 'respuesta': texto.strip()}

        return {
            'ok': False,
            'error': 'El asistente no está disponible en este momento.',
        }

    except requests.exceptions.Timeout:
        return {'ok': False, 'error': 'El asistente tardó demasiado en responder.'}
    except Exception:
        return {'ok': False, 'error': 'No se pudo contactar al asistente.'}
