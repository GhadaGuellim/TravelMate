from django.urls import path

from .dashboard import DashboardView
from .views import (
    LogView, ReportCreateView, ReportListView, ReportResolveView,
    StatsView, UserListView, UserStatusView,
)

urlpatterns = [
    path("report/", ReportCreateView.as_view()),
    path("stats/", StatsView.as_view()),
    path("dashboard/", DashboardView.as_view()),
    path("reports/", ReportListView.as_view()),
    path("reports/<str:report_id>/resolve/", ReportResolveView.as_view()),
    path("users/", UserListView.as_view()),
    path("users/<str:user_id>/status/", UserStatusView.as_view()),
    path("log/", LogView.as_view()),
]