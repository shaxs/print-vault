from django.db import migrations, models


def resolve_duplicate_active_scans(apps, schema_editor):
    """Before enforcing one active scan per root, finalize any pre-existing
    duplicates so the constraint can be added cleanly. Keep the newest
    pending/running scan per root; mark older ones as errored."""
    LibraryScan = apps.get_model('inventory', 'LibraryScan')
    seen_roots = set()
    for scan in (
        LibraryScan.objects.filter(status__in=['pending', 'running'])
        .order_by('root_id', '-created_at')
    ):
        if scan.root_id in seen_roots:
            scan.status = 'error'
            scan.error = (
                (scan.error + ' ' if scan.error else '')
                + '(auto-resolved duplicate active scan when adding the '
                'per-root uniqueness constraint)'
            )
            scan.save(update_fields=['status', 'error'])
        else:
            seen_roots.add(scan.root_id)


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0053_libraryfolder_tags_notes'),
    ]

    operations = [
        migrations.RunPython(resolve_duplicate_active_scans, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='libraryscan',
            constraint=models.UniqueConstraint(
                condition=models.Q(status__in=['pending', 'running']),
                fields=['root'],
                name='uniq_active_library_scan_per_root',
            ),
        ),
    ]
