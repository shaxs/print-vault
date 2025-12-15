from django.core.management.base import BaseCommand
from inventory.models import FilamentSpool


class Command(BaseCommand):
    help = 'Fix empty string NFC tag IDs by setting them to NULL'

    def handle(self, *args, **options):
        # Update all spools with empty string nfc_tag_id to NULL
        updated_count = FilamentSpool.objects.filter(nfc_tag_id='').update(nfc_tag_id=None)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} spool(s) with empty NFC tag IDs'
            )
        )
