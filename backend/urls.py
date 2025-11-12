# printvault/backend/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from inventory import views

router = DefaultRouter()
router.register(r'brands', views.BrandViewSet)
router.register(r'parttypes', views.PartTypeViewSet)
router.register(r'locations', views.LocationViewSet)
router.register(r'materials', views.MaterialViewSet)
router.register(r'vendors', views.VendorViewSet)
router.register(r'inventoryitems', views.InventoryItemViewSet)
router.register(r'printers', views.PrinterViewSet)
router.register(r'projects', views.ProjectViewSet)
router.register(r'projectinventory', views.ProjectInventoryViewSet)
router.register(r'projectprinters', views.ProjectPrintersViewSet)
router.register(r'mods', views.ModViewSet)
router.register(r'modfiles', views.ModFileViewSet)
router.register(r'projectlinks', views.ProjectLinkViewSet)
router.register(r'projectfiles', views.ProjectFileViewSet)
router.register(r'reminders', views.ReminderViewSet, basename='reminders')
router.register(r'low-stock', views.LowStockItemsViewSet, basename='lowstock')
router.register(r'trackers', views.TrackerViewSet)  # Print Tracker endpoints
router.register(r'tracker-files', views.TrackerFileViewSet)  # Tracker File endpoints

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/version/', views.VersionView.as_view(), name='version'),
    path('api/version/check-update/', views.CheckUpdateView.as_view(), name='check-update'),
    path('api/dashboard/', views.DashboardDataView.as_view(), name='dashboard'),
    path('api/alerts/dismiss/', views.DismissAlertView.as_view(), name='dismiss-alert'),
    path('api/alerts/dismiss-all/', views.DismissAllAlertsView.as_view(), name='dismiss-all-alerts'),
    path('api/export/data/', views.ExportDataView.as_view(), name='export-data'),
    path('api/validate-backup/', views.ValidateBackupView.as_view(), name='validate-backup'),
    path('api/import-data/', views.ImportDataView.as_view(), name='import-data'),
    path('api/delete-all-data/', views.DeleteAllData.as_view(), name='delete-all'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)