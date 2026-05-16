# apps/accounts/management/commands/create_superadmin.py
from django.core.management.base import BaseCommand
from notebook.accounts.models import User

class Command(BaseCommand):
    help = 'Superadmin yaratish'

    def handle(self, *args, **kwargs):
        username = input('Username: ')
        password = input('Parol: ')

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'{username} allaqachon mavjud!'))
            return

        user = User.objects.create_superuser(
            username=username,
            password=password,
            role='superadmin'
        )
        self.stdout.write(self.style.SUCCESS(f'✅ Superadmin yaratildi: {user.username}'))