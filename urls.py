from rest_framework import routers
from django.urls import path, include
from api.viewsets.user import UserViewSet
from api.viewsets.track import TrackViewSet
from api.viewsets.wallet import WalletViewSet
from api.viewsets.siem import SIEMEventViewSet, SeverityLevelViewSet
from api.viewsets.royalty import RoyaltyViewSet
from api.viewsets.split import SplitViewSet
from api.viewsets.payout import PayoutViewSet, PayoutStatusViewSet
from api.auth_views import get_auth_token, register_user

# =====================================================
# DRF Router
# =====================================================
router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'tracks', TrackViewSet, basename='track')
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'siem-events', SIEMEventViewSet, basename='siem-event')
router.register(r'royalties', RoyaltyViewSet, basename='royalty')
router.register(r'splits', SplitViewSet, basename='split')
router.register(r'payouts', PayoutViewSet, basename='payout')
router.register(r'payout-status', PayoutStatusViewSet, basename='payout-status')
router.register(r'severity-levels', SeverityLevelViewSet, basename='severity-level')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', get_auth_token, name='get-auth-token'),
    path('register/', register_user, name='register-user'),
]

