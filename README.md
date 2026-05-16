# ExamPlanner — Backend Django

API REST para la app ExamPlanner. Sprint 1 completo.

## Endpoints disponibles

| Método | URL | Descripción |
|--------|-----|-------------|
| POST | /api/auth/registro/ | Crear cuenta con @tecsup.edu.pe |
| POST | /api/auth/login/ | Iniciar sesión → devuelve JWT |
| POST | /api/auth/logout/ | Cerrar sesión |
| GET | /api/canvas/autorizar/ | URL OAuth para conectar Canvas |
| GET | /api/canvas/callback/ | Callback de Canvas tras autorizar |
| POST | /api/canvas/conectar/ | Conectar con token personal de Canvas |
| POST | /api/canvas/sincronizar/ | Re-importar tareas desde Canvas |
| GET | /api/pendientes/ | Tareas y exámenes pendientes combinados |
| GET/POST | /api/tareas/ | Listar o crear tareas manuales |
| GET/PUT/DELETE | /api/tareas/<id>/ | Detalle, editar o eliminar tarea |
| PATCH | /api/tareas/<id>/completar/ | Marcar tarea como completada |
| GET/POST | /api/examenes/ | Listar o registrar exámenes manuales |

## Instalación

```bash
# 1. Crear entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Edita .env con tus datos

# 4. Crear tablas en la base de datos
python manage.py makemigrations
python manage.py migrate

# 5. Crear superusuario para el panel admin
python manage.py createsuperuser

# 6. Correr el servidor
python manage.py runserver
```

El servidor queda en: http://localhost:8000
Panel admin en:       http://localhost:8000/admin/

## Uso básico con Postman

### 1. Registrarse
```
POST http://localhost:8000/api/auth/registro/
Content-Type: application/json

{
    "email": "anthony.arana@tecsup.edu.pe",
    "nombre": "Anthony Arana",
    "password": "mipassword123",
    "password_confirmacion": "mipassword123"
}
```

### 2. Login
```
POST http://localhost:8000/api/auth/login/
Content-Type: application/json

{
    "email": "anthony.arana@tecsup.edu.pe",
    "password": "mipassword123"
}
```
Guarda el `access` token de la respuesta.

### 3. Conectar Canvas (token personal)
```
POST http://localhost:8000/api/canvas/conectar/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "token": "tu_token_personal_de_canvas"
}
```
Obtén tu token en Canvas → Configuración → Tokens de acceso aprobados → + Token

### 4. Ver pendientes
```
GET http://localhost:8000/api/pendientes/
Authorization: Bearer <access_token>
```

### 5. Marcar tarea como completada
```
PATCH http://localhost:8000/api/tareas/1/completar/
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "completada": true
}
```

## Conectar Canvas sin OAuth (para desarrollo)

Si no tienes las credenciales OAuth de Tecsup, puedes conectar Canvas
usando un token personal:

1. Entra a Canvas → Configuración (esquina superior derecha)
2. Desplázate hasta "Tokens de acceso aprobados"
3. Clic en "+ Token de acceso nuevo"
4. Copia el token generado
5. Úsalo en el endpoint POST /api/canvas/conectar/
