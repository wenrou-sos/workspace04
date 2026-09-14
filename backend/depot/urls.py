from rest_framework.routers import DefaultRouter

from .views import (
    DashboardViewSet,
    FumigationTaskViewSet,
    GrainBatchViewSet,
    GranaryViewSet,
    LoginView,
    LogoutView,
    MeView,
    MonitorRecordViewSet,
    OperationLogViewSet,
    StockRecordViewSet,
    StocktakeItemViewSet,
    StocktakeViewSet,
    UserProfileViewSet,
)
from django.urls import path

router = DefaultRouter()
router.register("granaries", GranaryViewSet, basename="granary")
router.register("batches", GrainBatchViewSet, basename="batch")
router.register("monitors", MonitorRecordViewSet, basename="monitor")
router.register("stock-records", StockRecordViewSet, basename="stock-record")
router.register("fumigations", FumigationTaskViewSet, basename="fumigation")
router.register("stocktakes", StocktakeViewSet, basename="stocktake")
router.register("stocktake-items", StocktakeItemViewSet, basename="stocktake-item")
router.register("dashboard", DashboardViewSet, basename="dashboard")
router.register("operation-logs", OperationLogViewSet, basename="operation-log")
router.register("users", UserProfileViewSet, basename="user")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
]
urlpatterns += router.urls
