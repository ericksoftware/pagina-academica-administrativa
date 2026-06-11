# Aplicación Django

Este es un proyecto Django. A continuación, se detallan las instrucciones para clonar el repositorio y configurar el entorno de desarrollo local.

## Prerrequisitos

Antes de comenzar, asegúrate de tener instalado 
- Python 3.8 o superior, 
- Git 
- PostgreSQL (incluyendo pgAdmin).

## Instalación de PostgreSQL y pgAdmin

Descarga e instala PostgreSQL con la interfaz gráfica (pgAdmin) desde: [https://www.postgresql.org/download/](https://www.postgresql.org/download/)

Durante la instalación:

- Establece la contraseña para el usuario `postgres` como `1234`.
- Toma nota del puerto que se configura (por defecto es 5432).

Una vez instalado, abre pgAdmin y crea una nueva base de datos llamada `wasi_uni_db`.

## Configuración del proyecto

Clona el repositorio usando: `git clone [https://github.com/ericksoftware/benune.git](https://github.com/ericksoftware/pagina-academica-administrativa.git)` y entra al directorio con `cd proyecto`.

Crea un entorno virtual con `python -m venv venv`.

Activa el entorno virtual:
- En Windows usa `venv\Scripts\activate`.
- En macOS/Linux usa `source venv/bin/activate`.

Instala django con `pip install django`.

Instala las dependencias con `pip install -r requirements.txt`.

Configura la base de datos en `settings.py` reemplazando la sección `DATABASES` con:

    DATABASES = {

    'default': {

    'ENGINE': 'django.db.backends.postgresql',

    'NAME': 'wasisv_uni_db',

    'USER': 'postgres',

    'PASSWORD': '1234',

    'HOST': 'localhost',

    'PORT': '5432',

        }

    }


Aplica las migraciones con `python manage.py migrate`.

Opcionalmente, crea un superusuario para acceder al admin de Django con `python manage.py createsuperuser`.

Finalmente, ejecuta el servidor de desarrollo con `python manage.py runserver` y abre tu navegador en [http://localhost:8000](http://localhost:8000) para ver la aplicación.

## Notas adicionales

- Asegúrate de que el servicio de PostgreSQL esté ejecutándose antes de iniciar la aplicación Django.
- Si cambias la configuración de la base de datos (contraseña, nombre de BD, etc.), actualiza el archivo `settings.py` accordingly.
- El script `seed_demo_users.py` crea usuarios de prueba para poder probar la aplicación con datos iniciales.
