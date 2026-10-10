from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from destinations.models import Destination

# Garde ces tags identiques à TAGS dans le front (Destinations/utils.js)
DESTINATIONS = [
    {
        "name": "Tokyo", "country": "Japon",
        "description": "Mégapole électrique où temples centenaires, ruelles d'izakaya et quartiers futuristes se côtoient. Idéale pour la street food, la photo urbaine et des transports impeccables.",
        "best_season": "Mars – Mai", "avg_budget": 1500,
        "tags": ["Ville", "Gastronomie", "Culture", "Photographie"],
    },
    {
        "name": "Kyoto", "country": "Japon",
        "description": "Ancienne capitale impériale : temples, jardins zen, quartier de Gion et forêt de bambous d'Arashiyama. À parcourir tôt le matin pour éviter la foule.",
        "best_season": "Mars – Mai, Octobre – Novembre", "avg_budget": 1300,
        "tags": ["Culture", "Nature", "Photographie"],
    },
    {
        "name": "Bali", "country": "Indonésie",
        "description": "Rizières en terrasses, temples face à la mer, plages de surf et cafés de nomades numériques. Ubud pour la nature, Canggu pour les vagues.",
        "best_season": "Avril – Octobre", "avg_budget": 900,
        "tags": ["Plage", "Nature", "Aventure"],
    },
    {
        "name": "Lisbonne", "country": "Portugal",
        "description": "Capitale vallonnée aux tramways jaunes, aux azulejos et aux miradouros. Pastéis de nata, fado et couchers de soleil sur le Tage.",
        "best_season": "Avril – Juin, Septembre – Octobre", "avg_budget": 700,
        "tags": ["Ville", "Gastronomie", "Culture"],
    },
    {
        "name": "Marrakech", "country": "Maroc",
        "description": "Médina labyrinthique, souks colorés, jardin Majorelle et rooftops à l'heure du thé. Point de départ vers le désert d'Agafay et l'Atlas.",
        "best_season": "Octobre – Avril", "avg_budget": 650,
        "tags": ["Culture", "Gastronomie", "Ville"],
    },
    {
        "name": "Istanbul", "country": "Turquie",
        "description": "Deux continents, une ville : Sainte-Sophie, bazar couvert, ferries sur le Bosphore et petits cafés de Karaköy.",
        "best_season": "Avril – Mai, Septembre – Novembre", "avg_budget": 800,
        "tags": ["Ville", "Culture", "Gastronomie"],
    },
    {
        "name": "Santorin", "country": "Grèce",
        "description": "Maisons blanches et dômes bleus suspendus au-dessus de la caldeira. Les couchers de soleil d'Oia sont célèbres dans le monde entier.",
        "best_season": "Mai – Octobre", "avg_budget": 1200,
        "tags": ["Plage", "Photographie", "Culture"],
    },
    {
        "name": "Rome", "country": "Italie",
        "description": "Colisée, Forum, fontaine de Trevi : deux mille ans d'histoire à ciel ouvert, et une cuisine qui vaut le voyage à elle seule.",
        "best_season": "Avril – Juin, Septembre – Octobre", "avg_budget": 900,
        "tags": ["Ville", "Culture", "Gastronomie"],
    },
    {
        "name": "Paris", "country": "France",
        "description": "Musées, cafés, quais de Seine et quartiers à explorer à pied. Montmartre, le Marais et la Butte-aux-Cailles pour sortir des sentiers battus.",
        "best_season": "Avril – Juin, Septembre", "avg_budget": 1100,
        "tags": ["Ville", "Culture", "Gastronomie"],
    },
    {
        "name": "Islande", "country": "Islande",
        "description": "Cascades, glaciers, sources chaudes et aurores boréales. Le road trip sur la route 1 est un grand classique.",
        "best_season": "Juin – Août (soleil de minuit), Septembre – Mars (aurores)", "avg_budget": 1800,
        "tags": ["Nature", "Aventure", "Photographie"],
    },
    {
        "name": "New York", "country": "États-Unis",
        "description": "Skyline, Central Park, quartiers à forte personnalité et culture à toute heure. Brooklyn pour les vues, Manhattan pour l'énergie.",
        "best_season": "Avril – Juin, Septembre – Novembre", "avg_budget": 2000,
        "tags": ["Ville", "Culture", "Photographie"],
    },
    {
        "name": "Djerba", "country": "Tunisie",
        "description": "Île aux plages de sable fin, village blanc de Houmt Souk, poteries de Guellala et synagogue de la Ghriba. Cuisine de la mer à chaque repas.",
        "best_season": "Mai – Octobre", "avg_budget": 450,
        "tags": ["Plage", "Culture", "Gastronomie"],
    },
]

COVER_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def find_cover(slug):
    """Cherche media/destinations/<slug>.jpg|png|webp et renvoie le chemin relatif."""
    root = getattr(settings, "MEDIA_ROOT", None)
    if not root:
        return ""
    for ext in COVER_EXTENSIONS:
        if (Path(root) / "destinations" / f"{slug}{ext}").exists():
            return f"destinations/{slug}{ext}"
    return ""


class Command(BaseCommand):
    help = "Crée ou met à jour le catalogue de destinations (idempotent)."

    def handle(self, *args, **options):
        created = updated = covers = 0
        for item in DESTINATIONS:
            slug = slugify(item["name"])
            dest = Destination.objects(slug=slug).first()
            is_new = dest is None
            if is_new:
                dest = Destination(slug=slug)

            for key, value in item.items():
                setattr(dest, key, value)

            cover = find_cover(slug)
            if cover:  # sinon on garde la couverture déjà enregistrée
                dest.cover = cover
                covers += 1

            dest.save()
            created += is_new
            updated += not is_new

        self.stdout.write(self.style.SUCCESS(
            f"{created} créée(s), {updated} mise(s) à jour, {covers} couverture(s) liée(s)."
        ))