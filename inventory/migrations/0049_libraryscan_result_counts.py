# Hand-written (makemigrations is user-run in this repo; verify with
# `python manage.py makemigrations --check --dry-run`).
# Adds per-scan result counters to LibraryScan so the Library Settings screen
# can show "what the last scan found" (N new, M updated, K removed).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0048_trackerthumbnailjob'),
    ]

    operations = [
        migrations.AddField(
            model_name='libraryscan',
            name='files_new',
            field=models.PositiveIntegerField(
                default=0, help_text='New files discovered by this scan'
            ),
        ),
        migrations.AddField(
            model_name='libraryscan',
            name='files_updated',
            field=models.PositiveIntegerField(
                default=0, help_text='Changed files reprocessed (stat mismatch)'
            ),
        ),
        migrations.AddField(
            model_name='libraryscan',
            name='files_deleted',
            field=models.PositiveIntegerField(
                default=0, help_text="Files soft-deleted by this scan's deletion sweep"
            ),
        ),
    ]
