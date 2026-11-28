from bson import ObjectId
from mongoengine.errors import ValidationError as MongoValidationError

from posts.models import Post
from reviews.models import Review
from users.models import User


def resolve_target(target_type, target_id):
    """Renvoie (auteur, extrait) ou None si la cible n'existe pas."""
    try:
        if target_type == "post":
            p = Post.objects(id=target_id).first()
            return (p.author, p.text[:300]) if p else None
        if target_type == "comment":
            post_id, _, cid = target_id.partition(":")
            p = Post.objects(id=post_id).first()
            c = next((c for c in p.comments if str(c.id) == cid), None) if p else None
            return (c.author, c.text[:300]) if c else None
        if target_type == "review":
            r = Review.objects(id=target_id).first()
            return (r.author, (r.comment or f"Note : {r.rating}/5")[:300]) if r else None
        if target_type == "user":
            u = User.objects(id=target_id).first()
            return (u, f"Profil de {u.full_name}") if u else None
    except MongoValidationError:
        return None
    return None


def delete_target(target_type, target_id):
    """Supprime le contenu. Renvoie True si quelque chose a été supprimé."""
    try:
        if target_type == "post":
            p = Post.objects(id=target_id).first()
            if p:
                p.delete()
                return True
        elif target_type == "comment":
            post_id, _, cid = target_id.partition(":")
            p = Post.objects(id=post_id).first()
            if p and any(str(c.id) == cid for c in p.comments):
                p.update(pull__comments__id=ObjectId(cid))
                return True
        elif target_type == "review":
            r = Review.objects(id=target_id).first()
            if r:
                r.delete()
                return True
    except MongoValidationError:
        pass
    return False