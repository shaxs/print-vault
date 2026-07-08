# Hand-written (dev-environment convention: makemigrations is run by the user;
# verify with `python manage.py makemigrations --check --dry-run`).
# Creates the STL/3MF Library models: LibraryRoot, LibraryFolder, LibraryFile,
# LibraryScan. See chat_docs/planning/STL_LIBRARY_FEATURE_PLAN.md.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0043_tracker_viewer_settings_trackerfileimage_auto_generated'),
    ]

    operations = [
        migrations.CreateModel(
            name='LibraryRoot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('path', models.CharField(help_text='Absolute path as visible to this app (e.g. the bind-mount point inside the container)', max_length=1024)),
                ('enabled', models.BooleanField(default=True)),
                ('rescan_interval_hours', models.PositiveIntegerField(blank=True, help_text='Periodic rescan interval in hours; NULL = manual rescans only', null=True)),
                ('last_scanned_at', models.DateTimeField(blank=True, null=True)),
                ('last_scan_status', models.CharField(choices=[('idle', 'Idle'), ('running', 'Running'), ('success', 'Success'), ('error', 'Error')], default='idle', max_length=16)),
                ('last_scan_error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Library Root',
                'verbose_name_plural': 'Library Roots',
            },
        ),
        migrations.CreateModel(
            name='LibraryFolder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('relative_path', models.CharField(db_index=True, max_length=1024)),
                ('status', models.CharField(choices=[('active', 'Active'), ('deleted', 'Deleted')], default='active', max_length=16)),
                ('last_seen_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('parent', models.ForeignKey(blank=True, help_text='NULL for the root directory itself', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='inventory.libraryfolder')),
                ('root', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='folders', to='inventory.libraryroot')),
            ],
            options={
                'verbose_name': 'Library Folder',
                'verbose_name_plural': 'Library Folders',
                'unique_together': {('root', 'relative_path')},
            },
        ),
        migrations.CreateModel(
            name='LibraryFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=255)),
                ('relative_path', models.CharField(db_index=True, max_length=1024)),
                ('extension', models.CharField(max_length=8)),
                ('size_bytes', models.PositiveBigIntegerField()),
                ('modified_time', models.DateTimeField()),
                ('sha256_hash', models.CharField(blank=True, db_index=True, help_text='NULL until first hash pass; NOT unique — legitimate duplicate files share a hash', max_length=64, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('deleted', 'Deleted')], default='active', max_length=16)),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to='library_file_thumbnails/')),
                ('bounding_box_x', models.FloatField(blank=True, null=True)),
                ('bounding_box_y', models.FloatField(blank=True, null=True)),
                ('bounding_box_z', models.FloatField(blank=True, null=True)),
                ('embedded_metadata', models.JSONField(blank=True, default=dict, help_text='Embedded 3MF slicer metadata; empty dict for .stl files')),
                ('last_seen_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('folder', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='inventory.libraryfolder')),
                ('root', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='inventory.libraryroot')),
            ],
            options={
                'verbose_name': 'Library File',
                'verbose_name_plural': 'Library Files',
                'unique_together': {('root', 'relative_path')},
            },
        ),
        migrations.CreateModel(
            name='LibraryScan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('success', 'Success'), ('error', 'Error')], default='pending', max_length=16)),
                ('error', models.TextField(blank=True)),
                ('files_seen', models.PositiveIntegerField(default=0)),
                ('files_queued', models.PositiveIntegerField(default=0, help_text='Files needing expensive processing (hash/render/parse)')),
                ('files_processed', models.PositiveIntegerField(default=0)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('folder', models.ForeignKey(blank=True, help_text='Subtree scope for a scoped rescan; NULL = full-root scan', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='scans', to='inventory.libraryfolder')),
                ('root', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scans', to='inventory.libraryroot')),
            ],
            options={
                'verbose_name': 'Library Scan',
                'verbose_name_plural': 'Library Scans',
                'ordering': ['-created_at'],
            },
        ),
    ]
