from datetime import timedelta

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from mongoengine import Q
from mongoengine.errors import ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.utils import notify
from users.models import User

from .models import ModerationLog, Report, now
from .permissions import IsAdmin
from .serializers import ReportCreateSerializer, ResolveSerializer, UserStatusSerializer
from .targets import delete_target, resolve_target

TAG = ["Modération"]
TYPE_LABEL = {"post": "Publication", "comment": "Commentaire", "review": "Avis", "user": "Profil"}
DAILY_LIMIT = 20


# ---------- helpers ----------

def valid(u):
    return u if hasattr(u, "full_name") else None


def to_int(value, default):
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


def iso(d):
    return d.isoformat() if d else None


def mini(u):
    u = valid(u)
    return {"id": str(u.id), "full_name": u.full_name, "avatar_url": u.avatar_url or ""} if u else None


def admin_user(u):
    u = valid(u)
    if not u:
        return None
    return {
        "id": str(u.id),
        "full_name": u.full_name,
        "email": u.email,
        "avatar_url": u.avatar_url or "",
        "role": u.role,
        "status": u.effective_status(),
        "suspended_until": iso(u.suspended_until),
        "status_reason": u.status_reason or "",
        "pending_reports": Report.objects(target_owner=u, status="pending").count(),
        "created_at": iso(u.created_at),
    }


def report_data(r):
    return {
        "id": str(r.id),
        "target_type": r.target_type,
        "target_id": r.target_id,
        "reason": r.reason,
        "details": r.details,
        "snapshot": r.snapshot,
        "status": r.status,
        "resolution": r.resolution,
        "created_at": iso(r.created_at),
        "handled_at": iso(r.handled_at),
        "handled_by": (valid(r.handled_by).full_name if valid(r.handled_by) else ""),
        "reporter": mini(r.reporter),
        "owner": admin_user(r.target_owner),
        "content_exists": resolve_target(r.target_type, r.target_id) is not None,
        "pending_on_target": Report.objects(
            target_type=r.target_type, target_id=r.target_id, status="pending"
        ).count(),
    }


def get_report(report_id):
    try:
        r = Report.objects(id=report_id).first()
    except MongoValidationError:
        r = None
    if not r:
        raise NotFound("Signalement introuvable.")
    return r


def get_user(user_id):
    try:
        u = User.objects(id=user_id).first()
    except MongoValidationError:
        u = None
    if not u:
        raise NotFound("Utilisateur introuvable.")
    return u


def apply_sanction(user, sanction, days, reason):
    reason = (reason or "Non-respect des règles de la communauté")[:300]
    if sanction == "ban":
        user.update(set__status="banned", set__suspended_until=None, set__status_reason=reason)
        return "Compte banni"
    if sanction == "suspend":
        user.update(set__status="suspended", set__suspended_until=now() + timedelta(days=days),
                    set__status_reason=reason)
        return f"Suspendu {days} jour{'s' if days > 1 else ''}"
    return ""


# ---------- côté utilisateur ----------

class ReportCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ReportCreateSerializer, responses={201: OpenApiTypes.OBJECT}, tags=TAG)
    def post(self, request):
        me = request.user.user
        s = ReportCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        found = resolve_target(d["target_type"], d["target_id"])
        if not found:
            raise NotFound("Contenu introuvable ou déjà supprimé.")
        owner, excerpt = found
        owner = valid(owner)
        if owner is not None and owner.id == me.id:
            raise ValidationError("Tu ne peux pas signaler ton propre contenu.")
        if Report.objects(reporter=me, target_type=d["target_type"], target_id=d["target_id"]).first():
            raise ValidationError("Tu as déjà signalé ce contenu.")
        today = now().replace(hour=0, minute=0, second=0, microsecond=0)
        if Report.objects(reporter=me, created_at__gte=today).count() >= DAILY_LIMIT:
            raise ValidationError("Limite de signalements atteinte pour aujourd'hui.")

        Report(
            reporter=me, target_type=d["target_type"], target_id=d["target_id"],
            target_owner=owner, reason=d["reason"], details=d["details"], snapshot=excerpt,
        ).save()
        return Response(
            {"detail": "Merci, ton signalement a été transmis à l'équipe de modération."},
            status=status.HTTP_201_CREATED,
        )


# ---------- côté administrateur ----------

class StatsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=TAG)
    def get(self, request):
        return Response({
            "pending_reports": Report.objects(status="pending").count(),
            "handled_reports": Report.objects(status__ne="pending").count(),
            "suspended_users": User.objects(status="suspended").count(),
            "banned_users": User.objects(status="banned").count(),
            "total_users": User.objects.count(),
        })


class ReportListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        parameters=[
            OpenApiParameter("status", str, description="pending (défaut), resolved, dismissed, all"),
            OpenApiParameter("target_type", str),
            OpenApiParameter("limit", int),
            OpenApiParameter("skip", int),
        ],
        responses={200: OpenApiTypes.OBJECT},
        tags=TAG,
    )
    def get(self, request):
        p = request.query_params
        qs = Report.objects
        st = p.get("status", "pending")
        if st != "all":
            qs = qs.filter(status=st)
        if p.get("target_type"):
            qs = qs.filter(target_type=p["target_type"])
        limit = min(max(to_int(p.get("limit"), 30), 1), 50)
        skip = to_int(p.get("skip"), 0)
        order = "created_at" if st == "pending" else "-created_at"  # les plus anciens d'abord
        return Response([report_data(r) for r in qs.order_by(order).skip(skip).limit(limit)])


class ReportResolveView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(request=ResolveSerializer, responses={200: OpenApiTypes.OBJECT}, tags=TAG)
    def post(self, request, report_id):
        me = request.user.user
        report = get_report(report_id)
        if report.status != "pending":
            raise ValidationError("Ce signalement est déjà traité.")
        s = ResolveSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        owner = valid(report.target_owner)
        deleted, parts = False, []

        if d["action"] == "dismiss":
            new_status = "dismissed"
            parts.append("Aucune infraction constatée")
        else:
            if d["delete_content"] and report.target_type == "user":
                raise ValidationError("Un profil ne se supprime pas : applique une sanction.")
            if not d["delete_content"] and d["sanction"] == "none":
                raise ValidationError("Choisis une action, ou ignore le signalement.")
            if d["sanction"] != "none":
                if not owner:
                    raise ValidationError("Auteur introuvable.")
                if owner.role == "admin":
                    raise PermissionDenied("Tu ne peux pas sanctionner un administrateur.")
            if d["delete_content"]:
                deleted = delete_target(report.target_type, report.target_id)
                parts.append("Contenu supprimé" if deleted else "Contenu déjà supprimé")
            label = apply_sanction(owner, d["sanction"], d["days"], d["note"]) if d["sanction"] != "none" else ""
            if label:
                parts.append(label)
            new_status = "resolved"

        resolution = " · ".join(parts)
        pending = Report.objects(target_type=report.target_type, target_id=report.target_id, status="pending")
        reporters = [valid(r.reporter) for r in pending]
        pending.update(set__status=new_status, set__resolution=resolution,
                       set__handled_by=me, set__handled_at=now())

        ModerationLog(
            admin=me,
            action="report_dismissed" if d["action"] == "dismiss" else "report_resolved",
            target_user=owner,
            target_label=f"{TYPE_LABEL[report.target_type]} : {report.snapshot[:80]}",
            note=(resolution + (f" — {d['note']}" if d["note"] else ""))[:300],
        ).save()

        if owner and deleted and d["sanction"] != "ban":
            notify(owner, None, "moderation",
                   "Un de tes contenus a été supprimé : il ne respecte pas les règles de la communauté.",
                   {"section": "feed"})
        for rep in reporters:
            notify(rep, None, "moderation",
                   "Merci : ton signalement a été examiné par l'équipe de modération.",
                   {"section": "feed"})

        return Response(report_data(Report.objects(id=report.id).first()))


class UserListView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, description="Nom ou e-mail"),
            OpenApiParameter("status", str, description="active, suspended, banned"),
            OpenApiParameter("limit", int),
            OpenApiParameter("skip", int),
        ],
        responses={200: OpenApiTypes.OBJECT},
        tags=TAG,
    )
    def get(self, request):
        p = request.query_params
        qs = User.objects
        q = p.get("q", "").strip()
        if q:
            qs = qs.filter(Q(full_name__icontains=q) | Q(email__icontains=q))
        st = p.get("status")
        if st in ("suspended", "banned"):
            qs = qs.filter(status=st)
        elif st == "active":
            qs = qs.filter(status__nin=["suspended", "banned"])
        limit = min(max(to_int(p.get("limit"), 30), 1), 50)
        skip = to_int(p.get("skip"), 0)
        return Response([admin_user(u) for u in qs.order_by("-created_at").skip(skip).limit(limit)])


class UserStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(request=UserStatusSerializer, responses={200: OpenApiTypes.OBJECT}, tags=TAG)
    def post(self, request, user_id):
        me = request.user.user
        target = get_user(user_id)
        if target.id == me.id:
            raise ValidationError("Tu ne peux pas modifier ton propre compte.")
        if target.role == "admin":
            raise PermissionDenied("Tu ne peux pas modérer un administrateur.")
        s = UserStatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        if d["status"] == "active":
            target.update(set__status="active", set__suspended_until=None, set__status_reason="")
            label = "Compte réactivé"
        else:
            label = apply_sanction(target, "ban" if d["status"] == "banned" else "suspend", d["days"], d["reason"])

        ModerationLog(
            admin=me, action=f"user_{d['status']}", target_user=target,
            target_label=target.full_name, note=(label + (f" — {d['reason']}" if d["reason"] else ""))[:300],
        ).save()
        target.reload()
        return Response(admin_user(target))


class LogView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=TAG)
    def get(self, request):
        items = ModerationLog.objects.order_by("-created_at").limit(100)
        return Response([{
            "id": str(i.id),
            "action": i.action,
            "admin": (valid(i.admin).full_name if valid(i.admin) else ""),
            "target_user": (valid(i.target_user).full_name if valid(i.target_user) else ""),
            "target_label": i.target_label,
            "note": i.note,
            "created_at": iso(i.created_at),
        } for i in items])