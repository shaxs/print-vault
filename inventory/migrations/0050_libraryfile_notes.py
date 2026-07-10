from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0049_libraryscan_result_counts'),
    ]

    operations = [
        migrations.AddField(
            model_name='libraryfile',
            name='notes',
            field=models.TextField(
                blank=True,
                default='',
                help_text='User-authored free-form notes; searchable alongside the filename',
            ),
        ),
    ]
