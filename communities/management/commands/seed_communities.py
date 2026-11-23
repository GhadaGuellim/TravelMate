from django.core.management.base import BaseCommand

from communities.models import Community

# Les thèmes reprennent les catégories d'Explorer, pour matcher les préférences des profils.
# Les images sont dans le front : TravelMate_FrontEnd/public/communities/
COMMUNITIES = [
    {
        "name": "Solo Travelers",
        "description": "Conseils et rencontres pour voyager en solo.",
        "topics": ["Aventure", "Petit budget"],
        "cover_image": "/communities/solo-travelers.jpg",
    },
    {
        "name": "Asia Backpackers",
        "description": "Itinéraires et bons plans pour le sac à dos en Asie.",
        "topics": ["Aventure", "Nature", "Petit budget"],
        "cover_image": "/communities/asia-backpackers.jpg",
    },
    {
        "name": "Travel Photography",
        "description": "Partage tes plus belles photos de voyage.",
        "topics": ["Photographie", "Nature"],
        "cover_image": "/communities/travel-photography.jpg",
    },
    {
        "name": "Foodies Voyageurs",
        "description": "Découvre la gastronomie du monde entier.",
        "topics": ["Gastronomie", "Ville"],
        "cover_image": "/communities/foodies-voyageurs.jpg",
    },
    {
        "name": "Plages et Soleil",
        "description": "Les plus belles plages et escapades au soleil.",
        "topics": ["Plage", "Nature"],
        "cover_image": "/communities/plages-soleil.jpg",
    },
    {
        "name": "Culture et Patrimoine",
        "description": "Musées, sites historiques et traditions locales.",
        "topics": ["Culture", "Ville"],
        "cover_image": "/communities/culture-patrimoine.jpg",
    },
]


class Command(BaseCommand):
    help = "Crée ou met à jour les communautés prédéfinies (les membres sont conservés)."

    def handle(self, *args, **options):
        created = updated = 0
        for data in COMMUNITIES:
            community = Community.objects(name=data["name"]).first()
            if community is None:
                Community(**data).save()
                created += 1
            else:
                community.update(
                    set__description=data["description"],
                    set__topics=data["topics"],
                    set__cover_image=data["cover_image"],
                )
                updated += 1
        self.stdout.write(
            self.style.SUCCESS(f"{created} créée(s), {updated} mise(s) à jour.")
        )