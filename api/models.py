from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class EstudianteManager(BaseUserManager):
    def create_user(self, email, nombre, password=None):
        if not email:
            raise ValueError('El correo es obligatorio')
        if not email.endswith('@tecsup.edu.pe'):
            raise ValueError('Solo se permiten correos institucionales de Tecsup')
        email = self.normalize_email(email)
        user = self.model(email=email, nombre=nombre)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre, password=None):
        user = self.create_user(email, nombre, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class Estudiante(AbstractBaseUser, PermissionsMixin):
    """
    Usuario personalizado. Solo acepta correos @tecsup.edu.pe.
    Almacena el token de Canvas para importar tareas automáticamente.
    """
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=150)
    canvas_token = models.TextField(blank=True, null=True)
    canvas_user_id = models.CharField(max_length=100, blank=True, null=True)
    canvas_conectado = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = EstudianteManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    class Meta:
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'

    def __str__(self):
        return f'{self.nombre} ({self.email})'


class Tarea(models.Model):
    """
    Tarea académica. Puede venir de Canvas (canvas_id != None)
    o ser registrada manualmente por el estudiante.
    """
    ORIGEN_CHOICES = [
        ('canvas', 'Importada de Canvas'),
        ('manual', 'Registrada manualmente'),
    ]
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='tareas'
    )
    nombre = models.CharField(max_length=300)
    curso = models.CharField(max_length=200)
    fecha_limite = models.DateTimeField()
    completada = models.BooleanField(default=False)
    fecha_completada = models.DateTimeField(null=True, blank=True)
    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES, default='manual')
    canvas_id = models.CharField(max_length=100, blank=True, null=True)
    canvas_curso_id = models.CharField(max_length=100, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['fecha_limite']
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'

    def __str__(self):
        return f'{self.nombre} — {self.curso}'

    @property
    def dias_restantes(self):
        """
        Días de calendario que faltan, contados en hora de Perú.
        0 = vence hoy, 1 = mañana, etc.
        """
        if self.completada:
            return 0
        hoy = timezone.localdate()
        fecha_local = timezone.localtime(self.fecha_limite).date()
        return max(0, (fecha_local - hoy).days)

    @property
    def esta_vencida(self):
        """
        Vencida solo si la fecha límite (con su hora real) ya pasó.
        Se compara el instante exacto, no el día.
        """
        return not self.completada and timezone.now() > self.fecha_limite


class Examen(models.Model):
    """
    Examen del estudiante. Puede venir de Canvas o ser manual.
    """
    ORIGEN_CHOICES = [
        ('canvas', 'Importado de Canvas'),
        ('manual', 'Registrado manualmente'),
    ]
    estudiante = models.ForeignKey(
        Estudiante,
        on_delete=models.CASCADE,
        related_name='examenes'
    )
    curso = models.CharField(max_length=200)
    fecha = models.DateTimeField()
    descripcion = models.TextField(blank=True, null=True)
    origen = models.CharField(max_length=10, choices=ORIGEN_CHOICES, default='manual')
    canvas_id = models.CharField(max_length=100, blank=True, null=True)
    canvas_curso_id = models.CharField(max_length=100, blank=True, null=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['fecha']
        verbose_name = 'Examen'
        verbose_name_plural = 'Exámenes'

    def __str__(self):
        return f'Examen de {self.curso}'

    @property
    def dias_restantes(self):
        """
        Días de calendario que faltan para el examen, en hora de Perú.
        0 = es hoy, 1 = mañana, etc.
        """
        hoy = timezone.localdate()
        fecha_local = timezone.localtime(self.fecha).date()
        return max(0, (fecha_local - hoy).days)

    @property
    def proximo(self):
        """True si el examen es en menos de 48 horas (instante exacto)."""
        delta = self.fecha - timezone.now()
        return 0 <= delta.total_seconds() <= 172800
