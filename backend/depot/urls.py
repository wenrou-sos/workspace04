from rest_framework.routers import DefaultRouter

from .views import (
    DashboardViewSet,
    FumigationTaskViewSet,
    GrainBatchViewSet,
    GranaryViewSet,
    MonitorRecordViewSet,
    StockRecordViewSet,
    StocktakeItemViewSet,
    StocktakeViewSet,
)

router = DefaultRouter()
router.register("granaries", GranaryViewSet, basename="granary")
router.register("batches", GrainBatchViewSet, basename="batch")
router.register("monitors", MonitorRecordViewSet, basename="monitor")
router.register("stock-records", StockRecordViewSet, basename="stock-record")
router.register("fumigations", FumigationTaskViewSet, basename="fumigation")
router.register("stocktakes", StocktakeViewSet, basename="stocktake")
router.register("stocktake-items", StocktakeItemViewSet, basename="stocktake-item")
router.register("dashboard", DashboardViewSet, basename="dashboard")

urlpatterns = router.urls
