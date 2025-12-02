from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserAccountViewSet, RoleViewSet, TrackViewSet,
    StreamDataViewSet, RoyaltyViewSet, SplitViewSet,
    WalletViewSet, PayoutViewSet, PayoutStatusViewSet,
    SIEMEventViewSet, SeverityLevelViewSet
)

# Create DRF router
router = DefaultRouter()
router.register(r'users', UserAccountViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'tracks', TrackViewSet)
router.register(r'streams', StreamDataViewSet)
router.register(r'royalties', RoyaltyViewSet)
router.register(r'splits', SplitViewSet)
router.register(r'wallets', WalletViewSet)
router.register(r'payouts', PayoutViewSet)
router.register(r'payout-status', PayoutStatusViewSet)
router.register(r'siem-events', SIEMEventViewSet)
router.register(r'severity-levels', SeverityLevelViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
