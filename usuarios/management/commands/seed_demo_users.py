from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from usuarios.models import Usuario
from alumnos.models import Alumno
from evaluaciones.models import Carrera, Unidad, Materia, Calificacion


class Command(BaseCommand):
    help = "Crea o actualiza usuarios y datos demo para el portafolio WASISV."

    def handle(self, *args, **options):
        domain = getattr(settings, "SITE_EMAIL_DOMAIN", "wasisv.com")
        password = getattr(settings, "DEMO_LOGIN_PASSWORD", "12345678")
        periodo_demo = "2026-1"

        carrera = self.crear_carrera_demo()
        materias = self.crear_materias_demo(carrera)
        alumno = self.crear_alumno_demo(domain, password, carrera)
        self.crear_calificaciones_demo(alumno, materias, periodo_demo)
        self.crear_usuarios_demo(domain, password)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Datos demo creados/actualizados correctamente."))
        self.stdout.write("")
        self.stdout.write("Usuarios demo:")
        self.stdout.write(f"  admin@{domain} / {password}")
        self.stdout.write(f"  control@{domain} / {password}")
        self.stdout.write(f"  docente@{domain} / {password}")
        self.stdout.write(f"  alumno@{domain} / {password}")
        self.stdout.write("")
        self.stdout.write("Datos académicos demo:")
        self.stdout.write(f"  Carrera: {carrera.nombre} ({carrera.codigo})")
        self.stdout.write(f"  Alumno: {alumno.nombre_completo()} - {alumno.email_institucional}")
        self.stdout.write(f"  Periodo demo para calificaciones/actas: {periodo_demo}")

    def crear_usuarios_demo(self, domain, password):
        demo_users = [
            {
                "email": f"admin@{domain}",
                "username": "admin",
                "first_name": "Usuario",
                "last_name": "Administrador Demo",
                "tipo_usuario": "directivo",
                "is_staff": True,
                "is_superuser": True,
            },
            {
                "email": f"control@{domain}",
                "username": "control",
                "first_name": "Control",
                "last_name": "Escolar Demo",
                "tipo_usuario": "control_escolar",
                "is_staff": False,
                "is_superuser": False,
            },
            {
                "email": f"docente@{domain}",
                "username": "docente",
                "first_name": "Docente",
                "last_name": "Demo",
                "tipo_usuario": "docente",
                "is_staff": False,
                "is_superuser": False,
            },
        ]

        for data in demo_users:
            usuario = Usuario.objects.filter(
                Q(email=data["email"]) | Q(username=data["username"])
            ).first()

            if not usuario:
                usuario = Usuario()

            usuario.email = data["email"]
            usuario.username = data["username"]
            usuario.first_name = data["first_name"]
            usuario.last_name = data["last_name"]
            usuario.tipo_usuario = data["tipo_usuario"]
            usuario.turno = "matutino"

            usuario.curp = "N/A"
            usuario.rfc = "N/A"
            usuario.municipio_nacimiento = "N/A"
            usuario.sexo = "N/A"
            usuario.telefono = "N/A"
            usuario.email_personal = "N/A"

            usuario.is_active = True
            usuario.is_staff = data["is_staff"]
            usuario.is_superuser = data["is_superuser"]
            usuario.set_password(password)
            usuario.save()

            self.stdout.write(self.style.SUCCESS(f"Usuario demo listo: {usuario.email}"))

    def crear_carrera_demo(self):
        carrera = Carrera.objects.filter(codigo="ISW").first()

        if not carrera:
            carrera = Carrera()

        carrera.nombre = "Ingeniería en Software Demo"
        carrera.codigo = "ISW"
        carrera.tipo_carrera = "ingenieria"
        carrera.numero_semestres = 8
        carrera.plan = 2026
        carrera.activa = True
        carrera.save()

        self.stdout.write(self.style.SUCCESS(f"Carrera demo lista: {carrera.nombre}"))
        return carrera

    def crear_materias_demo(self, carrera):
        unidades = []

        for numero in range(1, 5):
            codigo = f"{carrera.codigo}{str(carrera.plan)[-2:]}{str(numero).zfill(2)}"

            unidad = Unidad.objects.filter(carrera=carrera, numero=numero).first()

            if not unidad:
                unidad = Unidad(carrera=carrera, numero=numero)

            unidad.codigo = codigo
            unidad.nombre = f"Unidad {numero}"
            unidad.save()

            unidades.append(unidad)

        materias_config = [
            {
                "unidad": unidades[0],
                "nombre": "Fundamentos de Programación",
                "semestre": 1,
                "parciales": 2,
                "creditos": 8.0,
                "horas": 64,
            },
            {
                "unidad": unidades[1],
                "nombre": "Bases de Datos",
                "semestre": 1,
                "parciales": 2,
                "creditos": 8.0,
                "horas": 64,
            },
            {
                "unidad": unidades[2],
                "nombre": "Desarrollo Web",
                "semestre": 1,
                "parciales": 2,
                "creditos": 8.0,
                "horas": 64,
            },
            {
                "unidad": unidades[3],
                "nombre": "Ingeniería de Software",
                "semestre": 1,
                "parciales": 2,
                "creditos": 8.0,
                "horas": 64,
            },
        ]

        materias = []

        for item in materias_config:
            materia = Materia.objects.filter(unidad=item["unidad"]).first()

            if not materia:
                materia = Materia(carrera=carrera, unidad=item["unidad"])

            materia.carrera = carrera
            materia.unidad = item["unidad"]
            materia.nombre = item["nombre"]
            materia.semestre = item["semestre"]
            materia.parciales = item["parciales"]
            materia.creditos = item["creditos"]
            materia.horas = item["horas"]
            materia.activa = True
            materia.save()

            materias.append(materia)
            self.stdout.write(self.style.SUCCESS(f"Materia demo lista: {materia.nombre}"))

        return materias

    def crear_alumno_demo(self, domain, password, carrera):
        alumno_email = f"alumno@{domain}"

        alumno = Alumno.objects.filter(matricula="DEMO-001").first()

        if not alumno:
            alumno = Alumno(matricula="DEMO-001")

        alumno.curp = "N/A"
        alumno.rfc = "N/A"

        alumno.nombre = "Alumno"
        alumno.apellido_paterno = "Demo"
        alumno.apellido_materno = "WASISV"

        alumno.municipio_nacimiento = "N/A"
        alumno.sexo = "N/A"

        alumno.institucion_procedencia = "N/A"
        alumno.municipio_institucion = "N/A"
        alumno.clave_escuela = "N/A"
        alumno.constancia_terminacion = "no"

        alumno.carrera = carrera
        alumno.promedio_semestre_anterior = 9.0
        alumno.semestre_actual = 1
        alumno.turno = "matutino"
        alumno.plan = carrera.plan
        alumno.grupo = "101"

        alumno.email_institucional = alumno_email
        alumno.password_email_institucional = password
        alumno.email_personal = "N/A"
        alumno.telefono = "N/A"

        alumno.estado = "activo"
        alumno.save()

        self.stdout.write(self.style.SUCCESS(f"Alumno demo listo: {alumno.email_institucional}"))

        return alumno

    def crear_calificaciones_demo(self, alumno, materias, periodo):
        valores_por_materia = [
            {
                "parcial_1": Decimal("9.00"),
                "parcial_2": Decimal("9.50"),
                "evidencia_final": Decimal("10.00"),
            },
            {
                "parcial_1": Decimal("8.50"),
                "parcial_2": Decimal("9.00"),
                "evidencia_final": Decimal("9.50"),
            },
            {
                "parcial_1": Decimal("9.50"),
                "parcial_2": Decimal("10.00"),
                "evidencia_final": Decimal("10.00"),
            },
            {
                "parcial_1": Decimal("8.00"),
                "parcial_2": Decimal("8.50"),
                "evidencia_final": Decimal("9.00"),
            },
        ]

        for materia, valores in zip(materias, valores_por_materia):
            Calificacion.objects.update_or_create(
                alumno=alumno,
                unidad=materia.unidad,
                periodo=periodo,
                tipo_calificacion="parcial",
                numero_parcial=1,
                defaults={
                    "calificacion": valores["parcial_1"],
                },
            )

            Calificacion.objects.update_or_create(
                alumno=alumno,
                unidad=materia.unidad,
                periodo=periodo,
                tipo_calificacion="parcial",
                numero_parcial=2,
                defaults={
                    "calificacion": valores["parcial_2"],
                },
            )

            Calificacion.objects.filter(
                alumno=alumno,
                unidad=materia.unidad,
                periodo=periodo,
                tipo_calificacion="evidencia_final",
                numero_parcial=None,
            ).delete()

            Calificacion.objects.create(
                alumno=alumno,
                unidad=materia.unidad,
                periodo=periodo,
                tipo_calificacion="evidencia_final",
                numero_parcial=None,
                calificacion=valores["evidencia_final"],
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Calificaciones demo listas: {alumno.matricula} - {materia.nombre}"
                )
            )