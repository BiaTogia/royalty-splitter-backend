from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from decimal import Decimal
from django.utils import timezone

from .models import (
    UserAccount, Role, Track, StreamData, Royalty, Split,
    Wallet, Payout, PayoutStatus, SIEM_Event, SeverityLevel
)

from .serializers import (
    UserAccountSerializer, RoleSerializer, TrackSerializer,
    StreamDataSerializer, RoyaltySerializer, SplitSerializer,
    WalletSerializer, PayoutSerializer, PayoutStatusSerializer,
    SIEMEventSerializer, SeverityLevelSerializer
)

from .royalty_service import distribute_royalty_for_track
from .services.blockchain import send_payout


# ==================================================
# UserAccount ViewSet
# ==================================================
class UserAccountViewSet(viewsets.ModelViewSet):
    queryset = UserAccount.objects.all()
    serializer_class = UserAccountSerializer
    permission_classes = [permissions.IsAuthenticated]


# ==================================================
# Royalty ViewSet (read-only)
# ==================================================
class RoyaltyViewSet(viewsets.ModelViewSet):
    queryset = Royalty.objects.all()
    serializer_class = RoyaltySerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        return Response(
            {"error": "Royalty creation is automatic and cannot be posted manually."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )


# ==================================================
# Track ViewSet (NO create() here)
# ==================================================
class TrackViewSet(viewsets.ModelViewSet):
    queryset = Track.objects.all()
    serializer_class = TrackSerializer
    permission_classes = [permissions.IsAuthenticated]


# ==================================================
# StreamData ViewSet
# ==================================================
class StreamDataViewSet(viewsets.ModelViewSet):
    queryset = StreamData.objects.all()
    serializer_class = StreamDataSerializer
    permission_classes = [permissions.IsAuthenticated]


# ==================================================
# Split ViewSet
# ==================================================
class SplitViewSet(viewsets.ModelViewSet):
    queryset = Split.objects.all()
    serializer_class = SplitSerializer
    permission_classes = [permissions.IsAuthenticated]


# ==================================================
# Wallet ViewSet
# ==================================================
class WalletViewSet(viewsets.ModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin hər şeyi görür
        if user.is_staff or (
            user.role and user.role.role_name.lower() == "admin"
        ):
            return Wallet.objects.all()

        # Normal user yalnız öz walletini görür
        return Wallet.objects.filter(user=user)

    def retrieve(self, request, *args, **kwargs):
        wallet = self.get_object()
        user = request.user

        if not (
            user.is_staff or
            (user.role and user.role.role_name.lower() == "admin") or
            wallet.user == user
        ):
            return Response(
                {"detail": "You do not have permission to view this wallet."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(wallet)
        return Response(serializer.data)

    # ------------------------------------------
    # Withdraw API
    # ------------------------------------------
    @action(detail=True, methods=['POST'], url_path='withdraw')
    def withdraw(self, request, pk=None):
        wallet = self.get_object()
        amount = request.data.get("amount")

        if amount is None:
            return Response({"error": "amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount))
        except:
            return Response({"error": "amount must be a number"}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"error": "amount must be > 0"}, status=status.HTTP_400_BAD_REQUEST)

        if amount > wallet.balance:
            return Response({"error": "amount exceeds wallet balance"}, status=status.HTTP_400_BAD_REQUEST)

        # Pending payouts
        pending_payouts = Payout.objects.filter(wallet=wallet, status__status_name="Pending")
        total_pending = sum(p.amount for p in pending_payouts)

        if amount > total_pending:
            return Response(
                {"error": "amount exceeds total pending payouts"},
                status=status.HTTP_400_BAD_REQUEST
            )

        completed_status, _ = PayoutStatus.objects.get_or_create(status_name="Completed")

        remaining = amount

        # Payout processing
        for payout in pending_payouts:
            if remaining <= 0:
                break

            if payout.amount <= remaining:
                remaining -= payout.amount
                payout.status = completed_status
                payout.save()
            else:
                # Partial payout
                Payout.objects.create(
                    wallet=wallet,
                    amount=remaining,
                    status=completed_status,
                    txn_date=timezone.now()
                )
                payout.amount -= remaining
                payout.save()
                remaining = Decimal("0")

        # Wallet balance update
        wallet.balance -= amount
        wallet.last_updated = timezone.now()
        wallet.save()

        # Blockchain transfer
        blockchain_result = send_payout(wallet.blockchain_address, float(amount))

        return Response({
            "message": f"Withdrawn {amount} successfully",
            "new_balance": wallet.balance,
            "blockchain": blockchain_result
        }, status=status.HTTP_200_OK)


# ==================================================
# Payout ViewSet
# ==================================================
class PayoutViewSet(viewsets.ModelViewSet):
    queryset = Payout.objects.all()
    serializer_class = PayoutSerializer
    permission_classes = [permissions.IsAuthenticated]


# ==================================================
# PayoutStatus ViewSet
# ==================================================
class PayoutStatusViewSet(viewsets.ModelViewSet):
    queryset = PayoutStatus.objects.all()
    serializer_class = PayoutStatusSerializer
    permission_classes = [permissions.IsAdminUser]


# ==================================================
# SIEM Event ViewSet
# ==================================================
class SIEMEventViewSet(viewsets.ModelViewSet):
    queryset = SIEM_Event.objects.all()
    serializer_class = SIEMEventSerializer
    permission_classes = [permissions.IsAdminUser]


# ==================================================
# SeverityLevel ViewSet
# ==================================================
class SeverityLevelViewSet(viewsets.ModelViewSet):
    queryset = SeverityLevel.objects.all()
    serializer_class = SeverityLevelSerializer
    permission_classes = [permissions.IsAdminUser]
