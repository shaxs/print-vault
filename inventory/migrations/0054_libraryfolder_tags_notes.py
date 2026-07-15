from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0053_libraryfile_is_favorite'),
    ]

    operations = [
        migrations.AddField(
            model_name='libraryfolder',
            name='notes',
            field=models.TextField(blank=True, default='', help_text='User-authored folder notes; folder-local — never cascades to files or subfolders. Matched by library search (name + notes).'),
        ),
        migrations.AddField(
            model_name='libraryfolder',
            name='tags',
            field=models.ManyToManyField(blank=True, help_text='Folder-level tags. Cascade DOWN into descendant folders and their files (copy-down model); never bubble up to a parent. See services/library_folder_tags.py.', related_name='library_folders', to='inventory.tag'),
        ),
    ]
