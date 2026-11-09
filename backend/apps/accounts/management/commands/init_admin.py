"""
Management command to provision or update the default administrator account.
Runs automatically on Docker container startup.
"""
from django.core.management.base import BaseCommand
# pyrefly: ignore [missing-import]
from apps.accounts.models import User, Role


class Command(BaseCommand):
    help = "Initializes default administrator account with full GIS & admin privileges"

    def handle(self, *args, **options):
        username = "sarvesh"
        email = "sarvesh112k@gmail.com"
        password = "sarvesh@suyal"

        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.filter(email=email).first()

        if user:
            user.username = username
            user.email = email
            user.set_password(password)
            user.role = Role.ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.first_name = "Sarvesh"
            user.last_name = "Suyal"
            user.organization = "Department of Land Resources"
            user.designation = "Administrator"
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Updated administrator account: {username} ({email})"))
        else:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                role=Role.ADMIN,
                first_name="Sarvesh",
                last_name="Suyal",
                organization="Department of Land Resources",
                designation="Administrator",
                is_active=True,
            )
            self.stdout.write(self.style.SUCCESS(f"Created administrator account: {username} ({email})"))
