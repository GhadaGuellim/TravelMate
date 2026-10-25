import random
from datetime import timedelta

from django.core.management.base import BaseCommand

from posts.models import Comment, Post, now
from users.models import User

SEED_DOMAIN = "@seed.travel"
PASSWORD = "Test1234!"

USERS = [
    {"name": "Amira Ben Salah", "slug": "amira", "city": "Tunis", "country": "Tunisie",
     "bio": "Photographe et grande curieuse. J'ai toujours un appareil photo dans mon sac.","avatar_url":"https://i.pravatar.cc/80?img=10",
     "preferences": "Culture, photographie, villes historiques"},
    {"name": "Youssef Trabelsi", "slug": "youssef", "city": "Sfax", "country": "Tunisie","avatar_url":"https://i.pravatar.cc/80?img=12",
     "bio": "Randonneur et amateur de street food. Je voyage léger.",
     "preferences": "Trek, nature, gastronomie"},
    {"name": "Lina Moreau", "slug": "lina", "city": "Lyon", "country": "France","avatar_url":"https://i.pravatar.cc/80?img=21",
     "bio": "Je prépare mon prochain tour du monde, un pays à la fois.",
     "preferences": "Backpacking, plages, rencontres"},
    {"name": "Karim Haddad", "slug": "karim", "city": "Alger", "country": "Algérie","avatar_url":"https://i.pravatar.cc/80?img=1",
     "bio": "Road trips et couchers de soleil dans le désert.",
     "preferences": "Désert, road trip, camping"},
    {"name": "Sofia Rossi", "slug": "sofia", "city": "Rome", "country": "Italie","avatar_url":"https://i.pravatar.cc/80?img=32",
     "bio": "Architecture, musées et bons restos. Dans cet ordre.",
     "preferences": "Art, architecture, city trip"},
    {"name": "Mehdi Jaziri", "slug": "mehdi", "city": "Sousse", "country": "Tunisie","avatar_url":"https://i.pravatar.cc/80?img=17",
     "bio": "Plongeur certifié. La mer, c'est ma maison.",
     "preferences": "Plongée, îles, surf"},
    {"name": "Emma Laurent", "slug": "emma", "city": "Montréal", "country": "Canada","avatar_url":"https://i.pravatar.cc/80?img=35",
     "bio": "Aventurière du froid : aurores boréales et chalets en bois.",
     "preferences": "Neige, aurores boréales, nature"},
    {"name": "Nour El Amri", "slug": "nour", "city": "Bizerte", "country": "Tunisie","avatar_url":"https://i.pravatar.cc/80?img=26",
     "bio": "Je cherche des travel mates pour partager des aventures.",
     "preferences": "Voyages entre amis, festivals, plages",},
]

# (index de l'auteur dans USERS, destination, texte, mot-clé image, ancienneté en heures)
POSTS = [
    (0, "Sidi Bou Saïd, Tunisie",
     "Les ruelles bleu et blanc au lever du soleil, sans personne. Le meilleur moment pour y aller, c'est avant 8h.",
     "sidibou", 3),
    (1, "Djerba, Tunisie",
     "Trois jours à Djerba : marché de Houmt Souk, plage de Sidi Mahrez et brik à l'œuf à chaque repas. Zéro regret.",
     "djerba", 7),
    (2, "Bali, Indonésie",
     "Première semaine à Ubud. Les rizières au petit matin, c'est irréel. Je loue un scooter demain pour aller vers le nord.",
     "bali", 14),
    (3, "Tozeur, Tunisie",
     "Road trip dans le sud : oasis, chott el-Jérid et nuit sous les étoiles. Prévoyez des vêtements chauds pour la nuit !",
     "tozeur", 26),
    (4, "Rome, Italie",
     "Astuce : le Panthéon est gratuit tôt le matin en semaine. Ensuite, cappuccino debout au comptoir comme les locaux.",
     "rome", 30),
    (5, "Zanzibar, Tanzanie",
     "Plongée à Mnemba : tortues, raies et une eau à 28 °C. J'ai passé plus de temps sous l'eau que sur terre.",
     "zanzibar", 40),
    (6, "Tromsø, Norvège",
     "Enfin vu les aurores boréales ! Il a fallu trois nuits et beaucoup de patience, mais ça valait chaque minute de froid.",
     "tromso", 52),
    (7, "Santorin, Grèce",
     "Quelqu'un pour partager un séjour à Santorin en septembre ? Je cherche des travel mates pour une semaine tranquille.",
     "santorin", 60),
    (1, "Ain Draham, Tunisie",
     "Randonnée en forêt de chênes-lièges sous la brume. Un coin trop méconnu, parfait pour un week-end nature.",
     "aindraham", 75),
    (0, "Marrakech, Maroc",
     "Se perdre dans la médina fait partie du voyage. Mon conseil : négociez avec le sourire, ça marche toujours.",
     "marrakech", 96),
    (2, "Lisbonne, Portugal",
     "Pastéis de nata, tramway 28 et fado le soir. Lisbonne est la ville la plus agréable à explorer à pied.",
     "lisbonne", 120),
    (3, "Tamanrasset, Algérie",
     "Lever du soleil depuis l'Assekrem. Le silence là-haut est difficile à décrire. À faire au moins une fois.",
     "assekrem", 150),
    (4, "Florence, Italie",
     "Montée au Piazzale Michelangelo au coucher du soleil. Toute la ville en or. Prévoyez un pique-nique.",
     "florence", 200),
    (6, "Banff, Canada",
     "Lac Moraine à l'aube : l'eau est d'un bleu irréel. Arrivez avant 6h pour éviter la foule.",
     "banff", 260),
]

COMMENTS = [
    "Magnifique ! Ça donne vraiment envie d'y aller 😍",
    "Merci pour le conseil, je note !",
    "J'y étais l'an dernier, je confirme, c'est incroyable.",
    "Superbe photo !",
    "Tu as logé où ? Je cherche une bonne adresse.",
    "Ça fait partie de ma liste pour l'année prochaine.",
    "Trop bien, merci du partage 🙏",
    "Combien de jours tu conseilles sur place ?",
    "Très belle destination, bon voyage !",
    "Je suis partant si tu cherches quelqu'un pour la prochaine fois !",
]


class Command(BaseCommand):
    help = "Insère des utilisateurs et des posts de démonstration dans MongoDB."

    def handle(self, *args, **options):
        random.seed(42)  # résultats reproductibles

        # 1. Nettoyage des anciennes données de démo (les posts sont supprimés en cascade)
        old = User.objects(email__endswith=SEED_DOMAIN)
        n_old = old.count()
        old.delete()
        if n_old:
            self.stdout.write(f"{n_old} anciens utilisateurs de démo supprimés.")

        # 2. Utilisateurs
        users = []
        for i, data in enumerate(USERS, start=1):
            u = User(
                email=f"{data['slug']}{SEED_DOMAIN}",
                full_name=data["name"],
                bio=data["bio"],
                city=data["city"],
                country=data["country"],
                preferences=data["preferences"],
                avatar_url=data["avatar_url"],
            )
            u.set_password(PASSWORD)
            u.save()
            users.append(u)
        self.stdout.write(self.style.SUCCESS(f"{len(users)} utilisateurs créés."))

        # 3. Abonnements : chacun suit 2 à 4 autres voyageurs
        for u in users:
            others = [x for x in users if x.id != u.id]
            u.following = random.sample(others, k=random.randint(2, 4))
            u.save()

        # 4. Posts
        for author_idx, destination, text, img_key, hours_ago in POSTS:
            author = users[author_idx]
            created = now() - timedelta(hours=hours_ago)

            others = [x for x in users if x.id != author.id]
            likes = random.sample(users, k=random.randint(1, len(users)))
            saved_by = random.sample(others, k=random.randint(0, 3))

            comments = []
            for j in range(random.randint(0, 4)):
                commenter = random.choice(others)
                comments.append(
                    Comment(
                        author=commenter,
                        text=random.choice(COMMENTS),
                        created_at=created + timedelta(minutes=random.randint(10, 600) * (j + 1)),
                    )
                )
            comments.sort(key=lambda c: c.created_at)

            Post(
                author=author,
                text=text,
                destination=destination,
                image=f"https://picsum.photos/seed/{img_key}/900/700",
                likes=likes,
                saved_by=saved_by,
                comments=comments,
                shares=random.randint(0, 12),
                created_at=created,
            ).save()

        self.stdout.write(self.style.SUCCESS(f"{len(POSTS)} posts créés."))
        self.stdout.write(
            f"\nConnexion de test : {USERS[0]['slug']}{SEED_DOMAIN} / {PASSWORD}"
        )