# Hand-written (dev-environment convention: makemigrations is run by the user;
# verify with `python manage.py makemigrations --check --dry-run`).
# Adds the AppConfiguration singleton that stores install-wide UI settings —
# currently sidebar module visibility (see
# chat_docs/planning/MODULE_VISIBILITY_FEATURE_PLAN.md).
#
# NOTE ON MIGRATION NUMBER: this branch is cut from `main` (latest migration
# 0043). The uncommitted STL/3MF Library feature on `feature/stl-library` ALSO
# introduces a 0044 (and 0045-0047). When these branches are reconciled, one of
# the two 0044s must be renumbered so the dependency chain stays linear.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0043_tracker_viewer_settings_trackerfileimage_auto_generated'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hidden_modules', models.JSONField(blank=True, default=list, help_text="List of sidebar module keys hidden from navigation, e.g. ['trackers', 'projects']. Empty list = every module visible. Stored as the HIDDEN set (not the visible set) so the default ([]) shows everything and unknown/legacy keys are simply ignored on read.")),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'App Configuration',
                'verbose_name_plural': 'App Configuration',
            },
        ),
    ]
