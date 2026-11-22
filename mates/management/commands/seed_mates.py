from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError

from trips.models import Trip
from users.models import User

DOMAIN = "@demo.travelmate.test"
PASSWORD = "Demo12345!"

# (identifiant, nom, ville, pays, intérêts, destination, début dans N jours, durée, budget)
PEOPLE = [
    ("sarah", "Sarah Martin", "Paris", "France",
     ["Plage", "Culture", "Gastronomie", "Villes"], "Tokyo", 10, 12, 1800),
    ("adam", "Adam Keller", "Berlin", "Allemagne",
     ["Randonnée", "Nature", "Aventure", "Road trip"], "Kyoto", 14, 12, 1500),
    ("lina", "Lina Haddad", "Tunis", "Tunisie",
     ["Plage", "Détente", "Gastronomie", "Culture"], "Djerba", 20, 7, 600),
    ("youssef", "Youssef Ben Salah", "Sousse", "Tunisie",
     ["Aventure", "Petit budget", "Voyage en groupe", "Randonnée"], "Bali", 30, 14, 900),
    ("chloe", "Chloé Dubois", "Lyon", "France",
     ["Villes", "Culture", "Vie nocturne", "Gastronomie"], "Lisbonne", 25, 6, 800),
    ("marco", "Marco Rossi", "Rome", "Italie",
     ["Road trip", "Plage", "Voyage en solo", "Nature"], "Santorin", 40, 8, 1200),
]


def as_date(d):
    return d.date() if isinstance(d, datetime) else d


class Command(BaseCommand):
    help = "Crée des comptes voyageurs de démonstration (idempotent) pour tester les suggestions."

    def add_arguments(self, parser):
        parser.add_argument("--like", help="E-mail d'un compte : Sarah copie ses intérêts et ses dates, Adam la même destination mais plus tard.")
        parser.add_argument("--clear", action="store_true", help="Supprime les comptes de démonstration et leurs voyages.")

    def handle(self, *args, **opts):
        if opts["clear"]:
            users = list(User.objects(email__endswith=DOMAIN))
            for u in users:
                Trip.objects(owner=u).delete()
                u.delete()
            self.stdout.write(self.style.SUCCESS(f"{len(users)} compte(s) de démonstration supprimé(s)."))
            return

        base = base_trip = None
        base_prefs = []
        if opts["like"]:
            base = User.objects(email=opts["like"].strip().lower()).first()
            if not base:
                raise CommandError("Aucun compte avec cet e-mail.")
            base_prefs = [p.strip() for p in (base.preferences or "").split(",") if p.strip()]
            base_trip = Trip.objects(owner=base, end_date__gte=date.today()).order_by("start_date").first()
            if not base_trip:
                self.stdout.write("Ce compte n'a pas de voyage à venir : les dates ne seront pas copiées.")

        today = date.today()
        for i, (slug, name, city, country, prefs, dest, offset, length, budget) in enumerate(PEOPLE):
            start = today + timedelta(days=offset)
            end = start + timedelta(days=length)

            if base and i == 0:
                prefs = base_prefs or prefs
                if base_trip:
                    dest = base_trip.destination
                    start = as_date(base_trip.start_date) + timedelta(days=2)
                    end = as_date(base_trip.end_date) + timedelta(days=2)
            elif base and i == 1:
                extra = [p for p in prefs if p not in base_prefs]
                prefs = base_prefs[:2] + extra[:2]
                if base_trip:
                    dest = base_trip.destination
                    start = as_date(base_trip.end_date) + timedelta(days=30)
                    end = start + timedelta(days=length)

            email = f"{slug}{DOMAIN}"
            user = User.objects(email=email).first() or User(email=email)
            user.full_name = name
            user.role = "traveler"
            user.city, user.country = city, country
            user.preferences = ", ".join(prefs)
            user.bio = f"Compte de démonstration ({name})."
            user.set_password(PASSWORD)
            user.save()

            Trip.objects(owner=user).delete()
            Trip(owner=user, title=f"{dest} avec {name.split()[0]}", destination=dest,
                 start_date=start, end_date=end, budget=budget).save()

        self.stdout.write(self.style.SUCCESS(f"{len(PEOPLE)} comptes de démonstration prêts."))
        self.stdout.write(f"Connexion : <identifiant>{DOMAIN} / {PASSWORD}  (ex. sarah{DOMAIN})")