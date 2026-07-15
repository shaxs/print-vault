from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0051_libraryfile_notes'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, help_text='Display name as the user typed it (trimmed)', max_length=50, unique=True)),
                ('slug', models.SlugField(db_index=True, help_text='Normalized identity for dedupe/lookup', max_length=60, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='libraryfile',
            name='tags',
            field=models.ManyToManyField(blank=True, help_text='User-applied labels; searchable and browseable', related_name='library_files', to='inventory.tag'),
        ),
    ]
