from django.core.management.base import BaseCommand, CommandError

from users.models import User


class Command(BaseCommand):
    help = "Donne (ou retire avec --remove) le rôle administrateur à un compte existant."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--remove", action="store_true")

    def handle(self, *args, **opts):
        user = User.objects(email=opts["email"].strip().lower()).first()
        if not user:
            raise CommandError("Aucun compte avec cet e-mail.")
        user.role = "traveler" if opts["remove"] else "admin"
        user.save()
        self.stdout.write(self.style.SUCCESS(f"{user.email} : rôle {user.role}."))