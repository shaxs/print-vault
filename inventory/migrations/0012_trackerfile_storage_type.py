# Generated migration to add per-file storage type tracking
from django.db import migrations, models


def set_initial_storage_types(apps, schema_editor):
    """
    Populate storage_type based on existing data:
    - If local_file exists → storage_type='local'
    - Otherwise → storage_type='link'
    """
    TrackerFile = apps.get_model('inventory', 'TrackerFile')
    
    for tracker_file in TrackerFile.objects.all():
        if tracker_file.local_file:
            tracker_file.storage_type = 'local'
        else:
            tracker_file.storage_type = 'link'
        tracker_file.save(update_fields=['storage_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0011_alter_tracker_github_url_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='trackerfile',
            name='storage_type',
            field=models.CharField(
                max_length=10,
                choices=[
                    ('link', 'Link Only'),
                    ('local', 'Downloaded/Uploaded')
                ],
                default='link',
                help_text='Storage method: link (GitHub URL only) or local (file on server)'
            ),
        ),
        migrations.RunPython(set_initial_storage_types, reverse_code=migrations.RunPython.noop),
    ]
