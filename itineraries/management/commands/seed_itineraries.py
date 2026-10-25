from django.core.management.base import BaseCommand

from itineraries.models import Day, Itinerary, Stop
from users.models import User

# (heure, titre, catégorie, lat, lng, coût)
DATA = [
    ("amira@seed.travel", "3 jours à Marrakech", "Marrakech, Maroc", [
        ("Arrivée et médina", [
            ("10:30", "Check-in au riad Yasmine", "stay", 31.6295, -7.9811, 800),
            ("12:30", "Déjeuner chez Nomad", "food", 31.6300, -7.9870, 180),
            ("15:00", "Place Jemaa el-Fna", "sight", 31.6258, -7.9891, 0),
        ]),
        ("Jardins et palais", [
            ("09:00", "Jardin Majorelle", "nature", 31.6417, -8.0033, 150),
            ("12:00", "Palais Bahia", "sight", 31.6216, -7.9831, 80),
            ("20:00", "Dîner à la Mamounia", "food", 31.6246, -7.9976, 70),
        ]),
        ("Atlas et retour", [
            ("08:00", "Vallée de l'Ourika", "nature", 31.2030, -7.6770, 300),
            ("18:30", "Aéroport Marrakech-Ménara", "transport", 31.6069, -8.0363, 250),
        ]),
    ]),
    ("sofia@seed.travel", "Week-end à Rome", "Rome, Italie", [
        ("Rome antique", [
            ("09:00", "Colisée", "sight", 41.8902, 12.4922, 1800),
            ("13:00", "Pasta chez Da Enzo", "food", 41.8895, 12.4767, 2500),
        ]),
        ("Rome baroque", [
            ("08:30", "Panthéon", "sight", 41.8986, 12.4769, 0),
            ("11:00", "Fontaine de Trevi", "sight", 41.9009, 12.4833, 0),
            ("17:00", "Piazza Navona", "sight", 41.8992, 12.4730, 0),
        ]),
    ]),
        ("youssef@seed.travel", "Djerba en 3 jours", "Djerba, Tunisie", [
        ("Houmt Souk et le fort", [
            ("09:30", "Souk de Houmt Souk", "sight", 33.8755, 10.8575, 0),
            ("11:00", "Borj el-Kebir", "sight", 33.8767, 10.8581, 10),
            ("13:00", "Brik à l'œuf et poisson grillé", "food", 33.8750, 10.8590, 35),
            ("17:00", "Port de pêche au coucher du soleil", "nature", 33.8790, 10.8560, 0),
        ]),
        ("Culture et villages", [
            ("09:00", "Erriadh (Djerbahood)", "sight", 33.8105, 10.8510, 0),
            ("11:30", "Musée de Guellala", "sight", 33.7230, 10.8590, 15),
            ("13:30", "Déjeuner chez l'habitant", "food", 33.7300, 10.8600, 40),
            ("16:00", "Atelier de poterie", "other", 33.7240, 10.8570, 30),
        ]),
        ("Plage et détente", [
            ("10:00", "Plage de Sidi Mahrez", "nature", 33.8200, 11.0100, 0),
            ("13:00", "Déjeuner au bord de l'eau", "food", 33.8180, 11.0050, 45),
            ("16:00", "Balade à cheval sur la plage", "nature", 33.8190, 11.0090, 60),
        ]),
    ]),
    ("lina@seed.travel", "Lisbonne à pied", "Lisbonne, Portugal", [
        ("Alfama et centre", [
            ("09:00", "Praça do Comércio", "sight", 38.7076, -9.1366, 0),
            ("10:30", "Château Saint-Georges", "sight", 38.7139, -9.1334, 15),
            ("12:30", "Déjeuner au Time Out Market", "food", 38.7063, -9.1459, 25),
            ("15:00", "Tramway 28 jusqu'à Graça", "transport", 38.7167, -9.1306, 3),
            ("18:30", "Coucher de soleil à Santa Luzia", "nature", 38.7117, -9.1296, 0),
        ]),
        ("Belém et LX Factory", [
            ("09:30", "Monastère des Jerónimos", "sight", 38.6979, -9.2068, 12),
            ("11:00", "Pastéis de Belém", "food", 38.6975, -9.2032, 8),
            ("12:00", "Tour de Belém", "sight", 38.6916, -9.2160, 8),
            ("15:00", "LX Factory", "other", 38.7035, -9.1785, 0),
            ("20:30", "Soirée fado à Alfama", "food", 38.7110, -9.1290, 45),
        ]),
        ("Excursion à Sintra", [
            ("09:00", "Train pour Sintra", "transport", 38.7980, -9.3870, 5),
            ("10:30", "Palais de la Pena", "sight", 38.7876, -9.3906, 14),
            ("14:00", "Déjeuner dans le centre historique", "food", 38.7970, -9.3880, 22),
        ]),
    ]),
    ("karim@seed.travel", "Road trip dans le sud tunisien", "Tozeur, Tunisie", [
        ("Tozeur et le chott", [
            ("10:00", "Médina de Tozeur (Ouled el-Hadef)", "sight", 33.9197, 8.1335, 0),
            ("12:30", "Déjeuner dans la palmeraie", "food", 33.9150, 8.1250, 30),
            ("15:30", "Traversée du chott el-Jérid", "nature", 33.7050, 8.3500, 0),
            ("19:00", "Nuit à Douz", "stay", 33.4600, 9.0200, 90),
        ]),
        ("Oasis de montagne", [
            ("09:00", "Cascade de Chebika", "nature", 34.3640, 7.9490, 5),
            ("11:00", "Tamerza", "sight", 34.3870, 7.9440, 0),
            ("13:00", "Pique-nique à Mides", "food", 34.4000, 7.9360, 15),
            ("17:00", "Retour à Tozeur", "transport", 33.9197, 8.1335, 40),
        ]),
        ("Désert et étoiles", [
            ("09:00", "Balade en dromadaire à Douz", "nature", 33.4560, 9.0300, 50),
            ("14:00", "Route vers Ksar Ghilane", "transport", 32.9890, 9.6190, 40),
            ("18:00", "Coucher de soleil sur les dunes", "nature", 32.9900, 9.6200, 0),
            ("20:00", "Nuit sous tente", "stay", 32.9880, 9.6180, 100),
        ]),
    ]),
    ("nour@seed.travel", "Santorin entre amis", "Santorin, Grèce", [
        ("Fira et Imerovigli", [
            ("10:00", "Arrivée et check-in à Fira", "stay", 36.4166, 25.4320, 120),
            ("12:30", "Déjeuner face à la caldeira", "food", 36.4170, 25.4300, 35),
            ("16:00", "Randonnée Fira – Imerovigli", "nature", 36.4290, 25.4270, 0),
            ("20:00", "Dîner de poisson", "food", 36.4280, 25.4260, 45),
        ]),
        ("Oia et coucher de soleil", [
            ("09:30", "Ruelles d'Oia le matin", "sight", 36.4618, 25.3753, 0),
            ("12:00", "Baignade à la baie d'Amoudi", "nature", 36.4590, 25.3720, 0),
            ("14:00", "Déjeuner de tavernes", "food", 36.4600, 25.3740, 30),
            ("19:00", "Coucher de soleil à Oia", "nature", 36.4625, 25.3730, 0),
        ]),
        ("Sud de l'île", [
            ("10:00", "Site archéologique d'Akrotiri", "sight", 36.3517, 25.4033, 12),
            ("12:30", "Plage Rouge", "nature", 36.3480, 25.3950, 0),
            ("15:30", "Dégustation de vins à Pyrgos", "food", 36.3830, 25.4500, 25),
        ]),
    ]),
]
COVERS = {
    "3 jours à Marrakech": "https://images.partir.com/Xh-qQ2jPKF8MeMkP-ON7ZBPw74s=/550x366/filters:sharpen(0.3,0.3,true)/lieux-interet/maroc/maroc-marrakech-place-el-fna.jpg",
    "Week-end à Rome": "https://qtxasset.com/quartz/qcloud1/media/image/travelagentcentral/1544476629/ColosseumRomevwalakteiStockGettyImagesPlusGettyImages.jpg/ColosseumRomevwalakteiStockGettyImagesPlusGettyImages.jpg?VersionId=8Wt_BNtEzqQ45ee8zdeFkLXdBecNFNnP",
    "Djerba en 3 jours": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSx5mrWZWuM2GuAGF73rfodqSyCvhoG5r9tkycn5iEKlynPnKes2TlZ7Do&s=10",
    "Lisbonne à pied": "https://s3.eu-west-1.amazonaws.com/ryo-prod-public-398019065442/public_weekend_lisbonne_visiter_2_3_4_jours_poster_91d6c77459.jpg",
    "Road trip dans le sud tunisien": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQBjr57tcZO-TUk8WcuvxuAlJS35PkKinh2tferwDPA4eLL-KDnLvNDVNQ&s=10",
    "Santorin entre amis": "https://media.cntraveller.com/photos/611be9bb69410e829d87e0c2/1:1/w_1280,h_1280,c_limit/Blue-domed-church-along-caldera-edge-in-Oia-Santorini-greece-conde-nast-traveller-11aug17-iStock.jpg",
}

class Command(BaseCommand):
    help = "Insère des itinéraires de démonstration (après seed_data)."

    def handle(self, *args, **options):
        for email, title, dest, days in DATA:
            author = User.objects(email=email).first()
            if not author:
                self.stdout.write(self.style.WARNING(f"{email} introuvable, lance seed_data d'abord."))
                continue
            Itinerary.objects(author=author, title=title).delete()
            Itinerary(
                author=author, title=title, destination=dest, is_public=True,
                cover=COVERS.get(title, ""),
                description="Itinéraire de démonstration.",
                days=[
                    Day(title=dt, stops=[
                        Stop(time=t, title=n, category=c, lat=la, lng=ln, cost=co)
                        for t, n, c, la, ln, co in stops
                    ])
                    for dt, stops in days
                ],
            ).save()
            self.stdout.write(self.style.SUCCESS(f"« {title} » créé."))