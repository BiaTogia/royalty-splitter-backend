from rest_framework import viewsets, permissions
from backend.models import Wallet
from api.serializers.wallet import WalletSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from django.utils import timezone
from backend.models import Payout, PayoutStatus
from backend.services.blockchain import send_payout


class WalletViewSet(viewsets.ModelViewSet):
    """
    CRUD + list for Wallets
    """
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Normal user yalnız öz wallet-ini görsün
        user = self.request.user
        if user.is_staff:  # admin bütün wallet-ləri görə bilir
            return Wallet.objects.all()
        return Wallet.objects.filter(user=user)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Return the current user's primary wallet (or first wallet)."""
        user = request.user
        wallets = Wallet.objects.filter(user=user)
        if not wallets.exists():
            return Response({'detail': 'Wallet not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(wallets.first())
        return Response(serializer.data)

    @action(detail=True, methods=['POST'], url_path='withdraw')
    def withdraw(self, request, pk=None):
        wallet = self.get_object()
        amount = request.data.get('amount')

        if amount is None:
            return Response({'error': 'amount is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount))
        except Exception:
            return Response({'error': 'amount must be a number'}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({'error': 'amount must be > 0'}, status=status.HTTP_400_BAD_REQUEST)

        if amount > wallet.balance:
            return Response({'error': 'amount exceeds wallet balance'}, status=status.HTTP_400_BAD_REQUEST)

        # Pending payouts
        pending_payouts = Payout.objects.filter(wallet=wallet, status__status_name='Pending')
        total_pending = sum((p.amount for p in pending_payouts), Decimal('0'))

        if amount > total_pending:
            return Response({'error': 'amount exceeds total pending payouts'}, status=status.HTTP_400_BAD_REQUEST)

        completed_status, _ = PayoutStatus.objects.get_or_create(status_name='Completed')

        remaining = amount

        for payout in pending_payouts:
            if remaining <= 0:
                break

            if payout.amount <= remaining:
                remaining -= payout.amount
                payout.status = completed_status
                payout.save()
            else:
                # Partial payout: create completed payout and reduce existing
                Payout.objects.create(
                    wallet=wallet,
                    amount=remaining,
                    status=completed_status,
                    txn_date=timezone.now()
                )
                payout.amount -= remaining
                payout.save()
                remaining = Decimal('0')

        # Wallet balance update
        wallet.balance -= amount
        wallet.last_updated = timezone.now()
        wallet.save()

        # Blockchain transfer
        blockchain_result = send_payout(wallet.blockchain_address, float(amount))

        return Response({
            'message': f'Withdrawn {amount} successfully',
            'new_balance': wallet.balance,
            'blockchain': blockchain_result
        }, status=status.HTTP_200_OK)
