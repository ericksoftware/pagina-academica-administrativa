from django.conf import settings


def site_branding(request):
    domain = getattr(settings, "SITE_EMAIL_DOMAIN", "wasisv.com")
    login_password = getattr(settings, "DEMO_LOGIN_PASSWORD", "12345678")

    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "WASISV"),
        "SITE_SHORT_NAME": getattr(settings, "SITE_SHORT_NAME", "WASISV"),
        "SITE_DESCRIPTION": getattr(
            settings,
            "SITE_DESCRIPTION",
            "Sistema académico demo para portafolio profesional",
        ),
        "SITE_EMAIL_DOMAIN": domain,
        "SITE_CONTACT_EMAIL": getattr(settings, "SITE_CONTACT_EMAIL", f"admin@{domain}"),

        "DEMO_LOGIN_PASSWORD": login_password,

        "DEMO_DELETE_PASSWORD_ALUMNOS": getattr(
            settings,
            "DEMO_DELETE_PASSWORD_ALUMNOS",
            "12345678",
        ),
        "DEMO_DELETE_PASSWORD_USUARIOS": getattr(
            settings,
            "DEMO_DELETE_PASSWORD_USUARIOS",
            "12345678",
        ),
        "DEMO_DELETE_PASSWORD_CARRERAS": getattr(
            settings,
            "DEMO_DELETE_PASSWORD_CARRERAS",
            "12345678",
        ),

        "DEMO_USERS": [
            {
                "role": "Administrador",
                "email": f"admin@{domain}",
                "password": login_password,
                "description": "Acceso general al sistema y panel de administración.",
            },
            {
                "role": "Control Escolar",
                "email": f"control@{domain}",
                "password": login_password,
                "description": "Gestión de alumnos, usuarios, carreras, constancias y actas.",
            },
            {
                "role": "Docente",
                "email": f"docente@{domain}",
                "password": login_password,
                "description": "Acceso a módulos académicos permitidos para docentes.",
            },
            {
                "role": "Alumno",
                "email": f"alumno@{domain}",
                "password": login_password,
                "description": "Acceso limitado a funciones disponibles para alumnos.",
            },
        ],
    }