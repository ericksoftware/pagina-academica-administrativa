from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('evaluaciones', '0003_materia_parciales_materia_unidad_nueva_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='materia',
            old_name='unidad_nueva',
            new_name='unidad',
        ),
        migrations.RemoveField(
            model_name='materia',
            name='unidades',
        ),
        migrations.AlterField(
            model_name='materia',
            name='unidad',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='materia',
                to='evaluaciones.unidad',
            ),
        ),
    ]