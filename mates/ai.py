import hashlib
import json
import os
import time

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
CACHE_TTL = 24 * 3600
_cache = {}  # clé -> (expiration, phrase)


def _norm(text):
    return " ".join((text or "").lower().split())


def _key(me, other, common, shared):
    raw = json.dumps([str(me.id), str(other.id), common, shared], sort_keys=True, default=str)
    return hashlib.sha1(raw.encode()).hexdigest()


def _looks_like_sentence(text):
    letters = sum(c.isalpha() for c in text)
    return (
        20 <= len(text) <= 300
        and letters >= 15
        and " " in text
        and text[-1] in ".!?…"
    )


def _facts(me, other, first, common, shared):
    facts = []
    if common:
        facts.append(f"Centres d'intérêt communs : {', '.join(common)}.")
    if shared:
        trip = f"{shared['destination']} du {shared['start']} au {shared['end']}"
        if shared.get("overlap"):
            facts.append(f"{first} voyage aussi à {trip}, à des dates qui chevauchent celles du lecteur.")
        else:
            facts.append(f"{first} voyage à {trip}, mais à d'autres dates que le lecteur.")
    if _norm(me.city) and _norm(me.city) == _norm(other.city):
        facts.append(f"{first} habite dans la même ville que le lecteur ({other.city}).")
    elif _norm(me.country) and _norm(me.country) == _norm(other.country):
        facts.append(f"{first} habite dans le même pays que le lecteur ({other.country}).")
    return facts


def generate_icebreaker(me, other, common, shared):
    """Renvoie une phrase d'accroche, ou None (clé absente, erreur, limite, réponse vide)."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    k = _key(me, other, common, shared)
    hit = _cache.get(k)
    if hit and hit[0] > time.time():
        return hit[1]

    first = ((other.full_name or "").split() or ["Ce voyageur"])[0]
    facts = _facts(me, other, first, common, shared)
    if not facts:  
        return None

    prompt = (
        f"Écris UNE seule phrase d'accroche en français (25 mots maximum), chaleureuse et naturelle, "
        f"pour suggérer à un voyageur de contacter {first}. Tutoie le lecteur. Parle de {first} à la "
        f"troisième personne et ne dis jamais que le lecteur voyage aux dates de {first}. "
        f"N'affirme jamais de compatibilité, de ressemblance ou de point commun qui ne figure pas "
        f"dans les faits. "
        f"Pas d'emoji ni de guillemets. Utilise uniquement ces faits : {' '.join(facts)}"
    )
    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1500,         # marge pour la réflexion + la phrase
                "reasoning_effort": "low",
                "temperature": 0.7,
            },
            timeout=20,
        )
        r.raise_for_status()
        choice = r.json()["choices"][0]
        text = (choice["message"].get("content") or "").strip().strip('"')
        finish = choice.get("finish_reason")
    except Exception as e:
        print("GROQ ERREUR :", repr(e))
        return None

    # réponse tronquée : on la refuse, la carte garde la phrase par règles
    if finish != "stop":
        print("GROQ réponse tronquée ignorée :", finish, repr(text[-40:]))
        return None

    if not _looks_like_sentence(text):
        print("GROQ réponse ignorée :", repr(text[:80]))
        return None

    _cache[k] = (time.time() + CACHE_TTL, text)
    return text