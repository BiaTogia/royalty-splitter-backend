from rest_framework import viewsets, permissions, status, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from backend.models import Payout, PayoutStatus, Wallet
from api.serializers.wallet import PayoutSerializer, PayoutStatusSerializer

class PayoutViewSet(viewsets.ModelViewSet):
    """
    CRUD for Payouts - Users can only view/manage their own payouts
    
    Endpoints:
    - GET /api/payouts/ - List user's payouts (filtered to authenticated user)
    - POST /api/payouts/ - Create payout (auto-assigns to user's wallet)
    - GET /api/payouts/{id}/ - Get payout details
    - PUT /api/payouts/{id}/ - Update payout
    - DELETE /api/payouts/{id}/ - Delete payout
    - GET /api/payouts/my_payouts/ - Get all payouts for authenticated user
    - GET /api/payouts/summary/ - Get payout summary
    """
    serializer_class = PayoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter payouts to only show user's own wallet payouts"""
        user = self.request.user
        try:
            user_wallet = user.wallet
            return Payout.objects.filter(wallet=user_wallet).order_by('-txn_date')
        except Wallet.DoesNotExist:
            return Payout.objects.none()
    
    def perform_create(self, serializer):
        """Auto-assign payout to authenticated user's wallet"""
        try:
            wallet = self.request.user.wallet
        except Wallet.DoesNotExist:
            raise serializers.ValidationError("User wallet does not exist")
        serializer.save(wallet=wallet)
    
    @action(detail=False, methods=['get'])
    def my_payouts(self, request):
        """Get all payouts for authenticated user"""
        user = request.user
        try:
            wallet = user.wallet
            payouts = Payout.objects.filter(wallet=wallet).order_by('-txn_date')
            serializer = self.get_serializer(payouts, many=True)
            return Response(serializer.data)
        except Wallet.DoesNotExist:
            return Response(
                {"error": "User wallet does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get payout summary for authenticated user"""
        user = request.user
        try:
            wallet = user.wallet
            payouts = Payout.objects.filter(wallet=wallet)
            total_amount = sum(p.amount for p in payouts)
            return Response({
                "total_payouts": payouts.count(),
                "total_amount": total_amount,
                "wallet_balance": wallet.balance
            })
        except Wallet.DoesNotExist:
            return Response(
                {"error": "User wallet does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )

class PayoutStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for Payout Statuses - Users cannot create/modify statuses
    """
    queryset = PayoutStatus.objects.all()
    serializer_class = PayoutStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
