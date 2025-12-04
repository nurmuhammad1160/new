from django.core.management.base import BaseCommand
from accounts.models import Region


class Command(BaseCommand):
    help = 'O\'zbekiston viloyatlarini bazaga qo\'shish'

    def handle(self, *args, **options):
        regions_data = [
            ('Toshkent shahri', 'TSH'),
            ('Toshkent viloyati', 'TOS'),
            ('Andijon', 'AND'),
            ('Buxoro', 'BUX'),
            ('Farg\'ona', 'FAR'),
            ('Jizzax', 'JIZ'),
            ('Xorazm', 'XOR'),
            ('Namangan', 'NAM'),
            ('Navoiy', 'NAV'),
            ('Qashqadaryo', 'QAS'),
            ('Qoraqalpog\'iston', 'QOR'),
            ('Samarqand', 'SAM'),
            ('Sirdaryo', 'SIR'),
            ('Surxondaryo', 'SUR'),
        ]

        created_count = 0
        for name, code in regions_data:
            region, created = Region.objects.get_or_create(
                code=code,
                defaults={'name': name}
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {name} yaratildi')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'○ {name} allaqachon mavjud')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nJami {created_count} ta yangi viloyat qo\'shildi!'
            )
        )