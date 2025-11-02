# create_test_users.py
import os
import sys
import django

# Path y settings
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
Usuario = get_user_model()

USUARIOS_DATA = [
    {
        'email': 'control@benune.edu.mx',
        'password': 'Control123',
        'first_name': 'María',
        'last_name': 'García López',
        'tipo_usuario': 'control_escolar',
        'turno': 'matutino',
        'telefono': '5551234567',
        'is_staff': True,
        'is_superuser': False,
    },
    {
        'email': 'directivo@benune.edu.mx',
        'password': 'Directivo123',
        'first_name': 'Carlos',
        'last_name': 'Rodríguez Martínez',
        'tipo_usuario': 'directivo',
        'turno': 'matutino',
        'telefono': '5557654321',
        'is_staff': True,
        'is_superuser': False,
    },
    {
        'email': 'docente@benune.edu.mx',
        'password': 'Docente123',
        'first_name': 'Ana',
        'last_name': 'Hernández Silva',
        'tipo_usuario': 'docente',
        'turno': 'vespertino',
        'telefono': '5559876543',
        'is_staff': False,
        'is_superuser': False,
    },
    {
        'email': 'admin@benune.edu.mx',
        'password': 'Admin123',
        'first_name': 'Super',
        'last_name': 'Administrador',
        'tipo_usuario': 'directivo',
        'turno': 'matutino',
        'telefono': '5550000000',
        'is_staff': True,
        'is_superuser': True,
    },
]

def ensure_user(email: str, password: str, **data):
    """
    Crea o actualiza un usuario de forma segura.
    - Detecta existencia por username (no cifrado).
    - Si existe: actualiza campos y contraseña.
    - Si no existe: crea con create_user() / create_superuser().
    """
    Usuario = get_user_model()
    username = email.split('@')[0]
    data.setdefault('username', username)

    # 🔎 Buscar por username (único y NO cifrado)
    usuario = Usuario.objects.filter(username=username).first()

    if usuario:
        # Actualizar existente
        for k, v in data.items():
            if k != 'username':  # mantener username
                setattr(usuario, k, v)
        usuario.email = email.lower()
        usuario.set_password(password)
        usuario.save()
        return usuario, False

    # Crear nuevo
    extra = {k: v for k, v in data.items() if k != 'username'}
    if data.get('is_superuser') and data.get('is_staff'):
        usuario = Usuario.objects.create_superuser(
            username, email=email.lower(), password=password, **extra
        )
    else:
        usuario = Usuario.objects.create_user(
            username, email=email.lower(), password=password, **extra
        )
    return usuario, True



def crear_usuario_control_escolar():
    base = {
        'email': 'control@benune.edu.mx',
        'password': 'Control123',
        'first_name': 'María',
        'last_name': 'García López',
        'tipo_usuario': 'control_escolar',
        'turno': 'matutino',
        'telefono': '5551234567',
        'is_staff': True,
        'is_superuser': False,
    }
    email = base.pop('email')
    pwd = base.pop('password')
    usuario, created = ensure_user(email, pwd, **base)
    print("✅ USUARIO CONTROL ESCOLAR CREADO:" if created else "🔄 USUARIO CONTROL ESCOLAR ACTUALIZADO:")
    print(f"   📧 {usuario.email} | 🔑 {pwd} | 👤 {usuario.get_full_name()} | 🏢 {usuario.get_tipo_usuario_display()}")


def crear_usuarios_prueba():
    print("🔧 Creando usuarios de prueba...")
    creados = 0
    actualizados = 0
    for item in USUARIOS_DATA:
        data = item.copy()
        email = data.pop('email')
        pwd = data.pop('password')  
        usuario, created = ensure_user(email, pwd, **data)
        if created:
            creados += 1
            print(f"✅ CREADO: {email} - {usuario.get_tipo_usuario_display()}")
        else:
            actualizados += 1
            print(f"🔄 ACTUALIZADO: {email} - {usuario.get_tipo_usuario_display()}")

    total = Usuario.objects.count()
    print(f"\n📊 Resumen:\n   Usuarios creados: {creados}\n   Usuarios actualizados: {actualizados}\n   Total en sistema: {total}")
    print("\n👥 Lista de usuarios:")
    for u in Usuario.objects.all():
        print(f"   • {u.email} - {u.get_tipo_usuario_display()} - {u.get_full_name()}")

if __name__ == '__main__':
    print("🚀 INICIANDO CREACIÓN DE USUARIOS DE PRUEBA")
    print("=" * 50)
    crear_usuario_control_escolar()
    print("\n" + "=" * 50)
    print("¿Deseas crear todos los usuarios de prueba?")
    if input("(s/n): ").strip().lower() == 's':
        print()
        crear_usuarios_prueba()
    print("\n🎉 Proceso completado!")
    print("\n💡 Credenciales de acceso:")
    print("   Control Escolar: control@benune.edu.mx / Control123")
    print("   Directivo:      directivo@benune.edu.mx / Directivo123")
    print("   Docente:        docente@benune.edu.mx / Docente123")
    print("   Admin:          admin@benune.edu.mx / Admin123")
