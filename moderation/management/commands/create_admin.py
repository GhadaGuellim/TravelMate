from getpass import getpass

from django.core.management.base import BaseCommand, CommandError

from users.models import User


class Command(BaseCommand):
    help = "Crée un compte administrateur."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("--name", default="Administrateur")
        parser.add_argument("--password", help="Sinon il est demandé au clavier.")

    def handle(self, *args, **opts):
        email = opts["email"].strip().lower()
        if User.objects(email=email).first():
            raise CommandError("Ce compte existe déjà. Utilise make_admin pour changer son rôle.")

        password = opts["password"] or getpass("Mot de passe (8 caractères minimum) : ")
        if len(password) < 8:
            raise CommandError("Mot de passe trop court.")

        user = User(email=email, full_name=opts["name"], role="admin")
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Administrateur créé : {email}"))