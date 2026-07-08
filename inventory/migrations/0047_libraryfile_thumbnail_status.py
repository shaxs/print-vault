# Hand-written (makemigrations is user-run in this repo; verify with
# `python manage.py makemigrations --check --dry-run`).
# Records WHY a library file does/doesn't have a preview so the UI can explain
# a missing thumbnail (too large vs unrenderable) instead of a blank box.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0046_libraryscan_kind'),
    ]

    operations = [
        migrations.AddField(
            model_name='libraryfile',
            name='thumbnail_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('rendered', 'Rendered'),
                    ('too_large', 'Too large'),
                    ('unrenderable', 'Unrenderable'),
                ],
                db_index=True,
                default='pending',
                help_text="Why a file does or doesn't have a preview, so the UI can explain a missing thumbnail",
                max_length=16,
            ),
        ),
    ]
