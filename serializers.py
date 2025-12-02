from rest_framework import serializers
from .models import (
    UserAccount, Role, Track, StreamData, Royalty, Split,
    Wallet, Payout, PayoutStatus, SIEM_Event, SeverityLevel
)


# =====================================================
# USER SERIALIZER
# =====================================================
class UserAccountSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = UserAccount
        fields = [
            'id', 'name', 'email', 'password',
            'role', 'country', 'is_active', 'is_staff'
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = UserAccount(**validated_data)
        user.set_password(password)
        user.save()
        return user


# =====================================================
# ROLE SERIALIZER
# =====================================================
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'role_name']


# =====================================================
# SPLITS
# =====================================================

# Read-only split serializer (Track GET cavabında görünür)
class SplitSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    track_id = serializers.IntegerField(source='track.id', read_only=True)

    class Meta:
        model = Split
        fields = ['id', 'track_id', 'user', 'user_email', 'percentage']


# Track yaratmaq üçün write-only split input
class SplitInputSerializer(serializers.Serializer):
    user = serializers.IntegerField()
    percentage = serializers.FloatField()

    def validate_user(self, value):
        if not UserAccount.objects.filter(id=value).exists():
            raise serializers.ValidationError("User does not exist")
        return value

    def validate_percentage(self, value):
        if not (0 <= value <= 100):
            raise serializers.ValidationError("Percentage must be between 0 and 100")
        return value


# =====================================================
# TRACK SERIALIZER (ÇOX VACİB)
# =====================================================
class TrackSerializer(serializers.ModelSerializer):
    # Read-only fields
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    splits = SplitSerializer(many=True, read_only=True)   # <-- Track GET cavabında göstərilən splits

    # Write-only fields
    splits_input = SplitInputSerializer(many=True, write_only=True)
    owner_counts = serializers.IntegerField(write_only=True)

    class Meta:
        model = Track
        fields = [
            'id', 'title', 'duration', 'genre', 'release_date',
            'nft_id', 'owner', 'owner_email',

            # write-only
            'owner_counts',
            'splits_input',

            # read-only
            'splits',
        ]

    def validate(self, data):
        splits = data.get("splits_input")
        owner_counts = data.get("owner_counts")

        if owner_counts != len(splits):
            raise serializers.ValidationError(
                f"owner_counts ({owner_counts}) does not match splits ({len(splits)})"
            )

        total_percentage = sum([s["percentage"] for s in splits])
        if round(total_percentage, 2) != 100.0:
            raise serializers.ValidationError(
                f"Total percentage must be 100, got {total_percentage}"
            )

        return data
    
    def create(self, validated_data):
        from datetime import date
        splits_data = validated_data.pop("splits_input")
        validated_data.pop("owner_counts", None)

        # Set release date automatically
        validated_data["release_date"] = date.today()

        # Create track
        track = Track.objects.create(**validated_data)

        # Create split records
        for split in splits_data:
            user = UserAccount.objects.get(id=split["user"])
            Split.objects.create(
                track=track,
                user=user,
                percentage=split["percentage"]
            )

        return track



# =====================================================
# STREAMDATA SERIALIZER
# =====================================================
class StreamDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = StreamData
        fields = [
            'id', 'track', 'platform',
            'stream_count', 'date_recorded', 'fraud_flag'
        ]


# =====================================================
# ROYALTY SERIALIZER
# =====================================================
class RoyaltySerializer(serializers.ModelSerializer):
    track_title = serializers.CharField(source='track.title', read_only=True)
    user_shares = serializers.SerializerMethodField()

    class Meta:
        model = Royalty
        fields = [
            'id', 'track', 'track_title',
            'total_earning', 'distribution_date',
            'user_shares'
        ]

    def get_user_shares(self, obj):
        return obj.get_user_shares()


# =====================================================
# PAYOUT + WALLET SERIALIZER
# =====================================================
class PayoutSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source='status.status_name', read_only=True)

    class Meta:
        model = Payout
        fields = [
            'id', 'amount', 'txn_date',
            'status', 'status_name', 'blockchain_txn_id'
        ]


class WalletSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    payouts = PayoutSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = [
            'id', 'user', 'user_email',
            'balance', 'blockchain_address',
            'last_updated', 'payouts'
        ]


# =====================================================
# PAYOUT STATUS SERIALIZER
# =====================================================
class PayoutStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutStatus
        fields = ['id', 'status_name']


# =====================================================
# SIEM EVENT SERIALIZER
# =====================================================
class SIEMEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SIEM_Event
        fields = [
            'id', 'user', 'event_type',
            'severity', 'timestamp', 'description'
        ]


# =====================================================
# SEVERITY LEVEL SERIALIZER
# =====================================================
class SeverityLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeverityLevel
        fields = ['id', 'severity_name']
