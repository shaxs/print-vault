from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0052_tag_libraryfile_tags'),
    ]

    operations = [
        migrations.AddField(
            model_name='libraryfile',
            name='is_favorite',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text='User-flagged favorite; filterable via the Show Favorites view',
            ),
        ),
    ]
