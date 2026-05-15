from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from alumnos.models import Alumno, normalizar_email_institucional


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()

        if not username or not password:
            return None

        username = username.strip().lower()

        print(f"🔐 Intentando autenticar: {username}")

        # PRIMERO: Buscar por username normal
        try:
            user = UserModel.objects.get(username=username)
            print(f"✅ Encontrado por username: {user.username}")

            if user and user.check_password(password):
                return user

        except UserModel.DoesNotExist:
            print("❌ No encontrado por username")

        except UserModel.MultipleObjectsReturned:
            user = UserModel.objects.filter(username=username).first()

            if user and user.check_password(password):
                return user

        # SEGUNDO: Buscar por email en usuarios
        try:
            user = UserModel.objects.get(email=username)
            print(f"✅ Encontrado por email: {user.email}")

            if user and user.check_password(password):
                return user

        except UserModel.DoesNotExist:
            print(f"❌ No encontrado por email: {username}")

        except UserModel.MultipleObjectsReturned:
            user = UserModel.objects.filter(email=username).first()
            print(f"✅ Múltiples usuarios con email, tomando primero: {user.email}")

            if user and user.check_password(password):
                return user

        # TERCERO: Buscar en alumnos activos
        try:
            print("🎓 Buscando alumno...")

            alumnos = Alumno.objects.filter(estado='activo')

            for alumno in alumnos:
                email_alumno = normalizar_email_institucional(alumno.email_institucional)

                if email_alumno in ['PENDIENTE', 'N/A']:
                    continue

                if email_alumno != username:
                    continue

                print(f"✅ Alumno encontrado: {alumno.nombre_completo()}")

                if alumno.password_email_institucional != password:
                    print("❌ Contraseña de alumno incorrecta")
                    return None

                print("✅ Contraseña de alumno válida")

                # Buscar usuario Django asociado
                usernames_posibles = alumno.obtener_usernames_posibles()

                user = UserModel.objects.filter(
                    username__in=usernames_posibles,
                    tipo_usuario='alumno'
                ).first()

                # Fallback: buscar por email
                if not user:
                    try:
                        user = UserModel.objects.get(
                            email=email_alumno,
                            tipo_usuario='alumno'
                        )
                    except UserModel.DoesNotExist:
                        user = None
                    except UserModel.MultipleObjectsReturned:
                        user = UserModel.objects.filter(
                            email=email_alumno,
                            tipo_usuario='alumno'
                        ).first()

                # Si no existe o está desactualizado, sincronizarlo
                if not user:
                    print("🔄 Usuario Django no encontrado. Creando/sincronizando...")
                    user = alumno.sincronizar_usuario_django()
                else:
                    email_user = (user.email or '').strip().lower()

                    if email_user != email_alumno or not user.check_password(password):
                        print("🔄 Usuario Django desactualizado. Sincronizando...")
                        user = alumno.sincronizar_usuario_django()

                if user:
                    print(f"✅ Usuario Django listo para login: {user.username}")
                    return user

                print("❌ No se pudo crear/sincronizar el usuario Django")
                return None

            print(f"❌ No se encontró alumno con email: {username}")

        except Exception as e:
            print(f"❌ Error buscando alumno: {e}")

        # CUARTO: Búsqueda manual como fallback
        try:
            print("🔄 Búsqueda manual en todos los usuarios...")

            for user in UserModel.objects.all():
                user_email = (user.email or '').strip().lower()
                user_username = (user.username or '').strip().lower()

                if user_email == username or user_username == username:
                    print(f"✅ Encontrado manualmente: {user.email}")

                    if user.check_password(password):
                        return user

        except Exception as e:
            print(f"❌ Error en búsqueda manual: {e}")

        print("❌ Autenticación fallida completamente")
        return None

    def get_user(self, user_id):
        UserModel = get_user_model()

        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None