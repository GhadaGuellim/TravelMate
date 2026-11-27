import logging
import re
from functools import lru_cache

from django.conf import settings
from openai import APIError, OpenAI, RateLimitError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .prompts import build_system_prompt

logger = logging.getLogger(__name__)

MAX_MESSAGES = 12  # taille max de l'historique envoyé au modèle
MAX_CHARS = 2000  # taille max d'un message


class ChatbotThrottle(UserRateThrottle):
    """Limite par utilisateur, pour maîtriser le coût de l'API."""

    scope = "chatbot"
    rate = "20/min"

    def get_cache_key(self, request, view):
        # Ton auth expose un AuthenticatedUser sans .pk : l'utilisateur Mongo est dans .user
        user = getattr(request.user, "user", None)
        ident = str(user.id) if user is not None else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


@lru_cache(maxsize=1)
def get_client():
    # Groq, Gemini, OpenRouter, Mistral... exposent tous une API compatible OpenAI :
    # changer de fournisseur = changer 3 variables d'environnement, pas le code.
    return OpenAI(api_key=settings.CHATBOT_API_KEY, base_url=settings.CHATBOT_BASE_URL)


def clean_messages(raw):
    """Valide l'historique envoyé par le front. Retourne (messages, erreur)."""
    if not isinstance(raw, list) or not raw:
        return None, "Une liste de messages est attendue."

    messages = []
    for m in raw[-MAX_MESSAGES:]:
        if not isinstance(m, dict):
            return None, "Format de message invalide."
        role, content = m.get("role"), m.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            return None, "Format de message invalide."
        content = content.strip()[:MAX_CHARS]
        if content:
            messages.append({"role": role, "content": content})

    # L'API exige que la conversation commence et finisse par un message "user".
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    if not messages or messages[-1]["role"] != "user":
        return None, "Le dernier message doit venir de l'utilisateur."
    return messages, None


class ChatbotView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ChatbotThrottle]

    def post(self, request):
        user = request.user.user

        messages, error = clean_messages(request.data.get("messages"))
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        if not settings.CHATBOT_API_KEY:
            return Response(
                {"detail": "L'assistant n'est pas configuré."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Les modèles gpt-oss « réfléchissent » avant de répondre et ces tokens comptent
        # dans max_tokens : on limite la réflexion et on garde une marge.
        extra = {}
        if settings.CHATBOT_MODEL.startswith("openai/gpt-oss"):
            extra["extra_body"] = {"reasoning_effort": "low"}

        try:
            response = get_client().chat.completions.create(
                model=settings.CHATBOT_MODEL,
                max_tokens=1500,
                temperature=0.7,
                **extra,
                messages=[
                    {"role": "system", "content": build_system_prompt(user)},
                    *messages,
                ],
            )
        except RateLimitError:
            # quota gratuit atteint (requêtes ou tokens par minute / par jour)
            return Response(
                {"detail": "L'assistant est très sollicité. Réessaie dans une minute."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except APIError as exc:
            # On garde la vraie cause dans la console du serveur (clé invalide,
            # modèle inconnu, URL incorrecte, réseau...).
            logger.error("Chatbot: erreur du fournisseur (%s): %s", type(exc).__name__, exc)
            detail = "L'assistant est momentanément indisponible. Réessaie dans un instant."
            if settings.DEBUG:
                detail += f" [{type(exc).__name__}: {exc}]"
            return Response({"detail": detail}, status=status.HTTP_502_BAD_GATEWAY)

        reply = (response.choices[0].message.content or "").strip()
        # certains modèles (Qwen...) laissent leur réflexion entre <think>...</think>
        reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
        return Response({"reply": reply or "Je n'ai pas de réponse pour le moment."})