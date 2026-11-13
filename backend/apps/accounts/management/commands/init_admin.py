
"""
Secure administrator bootstrap command.

Creates an administrator only when BOOTSTRAP_ADMIN=true.
Never stores administrator credentials in source code.
Does not reset an existing administrator's password on redeployment.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Role


class Command(BaseCommand):
    help = "Creates the initial administrator using environment variables."

    def handle(self, *args, **options):
        enabled = os.getenv("BOOTSTRAP_ADMIN", "false").lower() in {
            "1", "true", "yes", "on"
        }

        if not enabled:
            self.stdout.write(
                self.style.WARNING(
                    "Administrator bootstrap skipped. "
                    "Set BOOTSTRAP_ADMIN=true to enable it."
                )
            )
            return

        username = os.getenv("ADMIN_USERNAME", "").strip()
        email = os.getenv("ADMIN_EMAIL", "").strip()
        password = os.getenv("ADMIN_PASSWORD", "")

        if not username or not email or not password:
            raise CommandError(
                "ADMIN_USERNAME, ADMIN_EMAIL and ADMIN_PASSWORD "
                "must all be configured."
            )

        if len(password) < 12:
            raise CommandError(
                "ADMIN_PASSWORD must contain at least 12 characters."
            )

        User = get_user_model()

        existing_user = User.objects.filter(username=username).first()
        if existing_user:
            if existing_user.is_superuser and existing_user.role == Role.ADMIN:
                self.stdout.write(
                    self.style.WARNING(
                        f"Administrator '{username}' already exists. "
                        "No account details or password were changed."
                    )
                )
                return
            else:
                raise CommandError(
                    f"User '{username}' already exists but is not a verified administrator/superuser. "
                    "To prevent account takeover, no credentials or roles were modified automatically."
                )

        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(
                "An account with this email already exists. "
                "No administrator was created."
            )

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            role=Role.ADMIN,
            is_active=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Administrator '{username}' created successfully."
            )
        )
