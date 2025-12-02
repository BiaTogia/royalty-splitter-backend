from rest_framework import serializers
from backend.models import Wallet, Payout, PayoutStatus


class PayoutStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutStatus
        fields = ['id', 'status_name']


class PayoutSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source='status.status_name', read_only=True)

    class Meta:
        model = Payout
        fields = ['id', 'amount', 'txn_date', 'status', 'status_name', 'blockchain_txn_id']
        read_only_fields = ['id', 'status_name', 'txn_date']
    
    def validate_amount(self, value):
        """Validate payout amount is positive and within range"""
        from decimal import Decimal
        MIN_PAYOUT = Decimal('1.0')
        MAX_PAYOUT = Decimal('999999.99')
        
        if value <= 0:
            raise serializers.ValidationError("Payout amount must be positive.")
        if value < MIN_PAYOUT:
            raise serializers.ValidationError(f"Payout amount must be at least {MIN_PAYOUT}.")
        if value > MAX_PAYOUT:
            raise serializers.ValidationError(f"Payout amount cannot exceed {MAX_PAYOUT}.")
        return value
    
    def validate(self, data):
        """Validate wallet has sufficient balance for payout"""
        wallet = data.get('wallet')
        amount = data.get('amount')
        
        if wallet and amount:
            from decimal import Decimal
            if wallet.balance < Decimal(str(amount)):
                raise serializers.ValidationError(
                    f"Insufficient balance. Wallet balance: {wallet.balance}, Payout amount: {amount}"
                )
        return data


class WalletSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    payouts = PayoutSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = ['id', 'user', 'user_email', 'balance', 'blockchain_address', 'last_updated', 'payouts']
        read_only_fields = ['id', 'user_email', 'balance', 'last_updated', 'payouts']
