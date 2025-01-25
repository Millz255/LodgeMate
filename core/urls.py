# core/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api import UserViewSet
from .views import ReservationViewSet, InventoryItemViewSet, TransactionViewSet, ReportViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'reservations', ReservationViewSet)
router.register(r'inventory', InventoryItemViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'users', UserViewSet)
# Add basename to ReportViewSet
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
