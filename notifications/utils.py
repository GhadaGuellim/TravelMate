from .models import Notification


def notify(recipient, actor, type, text, target=None):
    """Crée une notification. Ne doit jamais faire échouer l'action principale."""
    try:
        if recipient is None or (actor is not None and recipient.id == actor.id):
            return
        target = target or {}
        already = Notification.objects(
            recipient=recipient, actor=actor, type=type, target=target, read=False
        ).first()
        if already:
            return
        Notification(
            recipient=recipient, actor=actor, type=type, text=text[:300], target=target
        ).save()
    except Exception:
        pass