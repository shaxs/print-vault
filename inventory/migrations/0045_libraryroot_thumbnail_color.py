# Hand-written (makemigrations is user-run in this repo; verify with
# `python manage.py makemigrations --check --dry-run`).
# Adds the user-selectable thumbnail/viewer render color to LibraryRoot.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0044_library_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='libraryroot',
            name='thumbnail_color',
            field=models.CharField(default='#94a3b8', help_text='Hex color used for rendered thumbnails and the 3D viewer (library files have no material context to derive one from)', max_length=7),
        ),
    ]
