from datetime import date, datetime

W_INTERESTS, W_DESTINATION, W_DATES, W_PROXIMITY = 0.40, 0.30, 0.20, 0.10
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
          "août", "septembre", "octobre", "novembre", "décembre"]


def icebreaker(other, common, shared, proximity):
    first = ((other.full_name or "").split() or ["Ce voyageur"])[0]
    if shared and shared.get("overlap"):
        if common:
            return (f"{first} part aussi à {shared['destination']} aux mêmes dates et aime "
                    f"{common[0].lower()} : de quoi organiser des sorties ensemble !")
        month = MONTHS[int(shared["start"][5:7]) - 1]
        return f"{first} sera à {shared['destination']} en {month} : une occasion de voyager à plusieurs."
    if shared:
        return (f"{first} voyage aussi à {shared['destination']}, mais à d'autres dates : "
                f"peut-être pour un prochain voyage.")
    if len(common) >= 2:
        return (f"Vous aimez tous les deux {common[0].lower()} et {common[1].lower()} : "
                f"{first} pourrait être un bon compagnon de route.")
    if common:
        return f"{first} partage ta passion pour {common[0].lower()}."
    if proximity == 1.0:
        return f"{first} habite aussi à {other.city} : un point de départ commun."
    return f"Peu de points communs avec {first} pour l'instant : complète ton profil pour de meilleures suggestions."

def norm(text):
    return " ".join((text or "").lower().split())


def as_date(d):
    return d.date() if isinstance(d, datetime) else d


def interests(user):
    """{'plage': 'Plage', ...} à partir de « Plage, Culture »."""
    return {norm(p): p.strip() for p in (user.preferences or "").split(",") if p.strip()}


def overlap_ratio(a_start, a_end, b_start, b_end):
    start, end = max(a_start, b_start), min(a_end, b_end)
    if end < start:
        return 0.0
    common = (end - start).days + 1
    shortest = max(min((a_end - a_start).days, (b_end - b_start).days) + 1, 1)
    return common / shortest

def gap_days(a_start, a_end, b_start, b_end):
    if a_end < b_start:
        return (b_start - a_end).days
    if b_end < a_start:
        return (a_start - b_end).days
    return 0


def compatibility(me, my_trips, other, other_trips):
    mine, theirs = interests(me), interests(other)
    common = sorted(mine.keys() & theirs.keys())
    union = mine.keys() | theirs.keys()
    jaccard = len(common) / len(union) if union else 0.0

    dest_score, date_score, shared = 0.0, 0.0, None
    for a in my_trips:
        a_s, a_e = as_date(a.start_date), as_date(a.end_date)
        for b in other_trips:
            if norm(a.destination) != norm(b.destination):
                continue
            b_s, b_e = as_date(b.start_date), as_date(b.end_date)
            ratio = overlap_ratio(a_s, a_e, b_s, b_e)
            if ratio > 0:
                d = 1.0
            elif gap_days(a_s, a_e, b_s, b_e) <= 14:
                d = 0.7
            else:
                d = 0.3
            if shared is None or (d, ratio) > (dest_score, date_score):
                dest_score, date_score, shared = d, ratio, b

    proximity = 0.0
    if norm(me.city) and norm(me.city) == norm(other.city):
        proximity = 1.0
    elif norm(me.country) and norm(me.country) == norm(other.country):
        proximity = 0.5

    score = round(100 * (W_INTERESTS * jaccard + W_DESTINATION * dest_score
                         + W_DATES * date_score + W_PROXIMITY * proximity))

    common_display = [theirs[k] for k in common]
    reasons = []
    if common_display:
        reasons.append(f"{len(common_display)} intérêt{'s' if len(common_display) > 1 else ''} en commun "
                       f"({', '.join(common_display)})")

    shared_trip = None
    if shared:
        s, e = as_date(shared.start_date), as_date(shared.end_date)
        overlap = date_score > 0
        shared_trip = {"destination": shared.destination, "start": s.isoformat(),
                       "end": e.isoformat(), "overlap": overlap}
        if overlap:
            reasons.append(f"{shared.destination} aux mêmes dates ({s:%d/%m} au {e:%d/%m})")
        else:
            reasons.append(f"Même destination ({shared.destination}), mais à d'autres dates "
                           f"({s:%d/%m} au {e:%d/%m})")

    if proximity == 1.0:
        reasons.append(f"Même ville : {other.city}")
    elif proximity == 0.5:
        reasons.append(f"Même pays : {other.country}")

    return {
        "score": min(score, 100),
        "reasons": reasons,
        "common_interests": common_display,
        "shared_trip": shared_trip,
        "icebreaker": icebreaker(other, common_display, shared_trip, proximity),
    }