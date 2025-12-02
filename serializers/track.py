from rest_framework import serializers
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from backend.models import Track, StreamData, Split, Royalty
from api.validators import FileValidator
from api.sanitizers import InputSanitizer

class StreamDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = StreamData
        fields = ['id', 'platform', 'stream_count', 'date_recorded', 'fraud_flag']
        read_only_fields = ['id']

class SplitSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(write_only=True, required=True)  # Accept email on input

    class Meta:
        model = Split
        fields = ['id', 'user', 'user_email', 'percentage', 'track']
        read_only_fields = ['id', 'user', 'track']  # Set by viewset/validate
        extra_kwargs = {
            'percentage': {'required': True},
        }

    def to_representation(self, instance):
        """Return user email in read representation"""
        ret = super().to_representation(instance)
        ret['user_email'] = instance.user.email
        return ret

    def validate_user_email(self, value):
        """Resolve user_email to user object"""
        from backend.models import UserAccount
        
        try:
            user = UserAccount.objects.get(email=value)
            # Store in context for later use
            self.context['_resolved_user'] = user
            return value
        except UserAccount.DoesNotExist:
            raise serializers.ValidationError(f"User with email '{value}' not found")

    def create(self, validated_data):
        """Create split with resolved user from context"""
        # Get user from validation context
        user = self.context.get('_resolved_user')
        if not user:
            raise serializers.ValidationError("User resolution failed")
        
        validated_data['user'] = user
        # Remove user_email since it's write_only
        validated_data.pop('user_email', None)
        
        return super().create(validated_data)

class RoyaltyDetailSerializer(serializers.ModelSerializer):
    track_title = serializers.CharField(source='track.title', read_only=True)
    user_shares = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Royalty
        fields = ['id', 'track', 'track_title', 'total_earning', 'distribution_date', 'user_shares']
        read_only_fields = ['id', 'track_title', 'user_shares']

    def get_user_shares(self, obj):
        return obj.get_user_shares()

    def get_genre_rate(self, genre):
        """Simple mapping of genre to royalty rate per minute."""
        rates = {
            'pop': 0.5,
            'rock': 0.6,
            'jazz': 0.4,
            'hiphop': 0.55,
        }
        return rates.get(genre.lower(), 0.5)

    def create(self, validated_data):
        track = validated_data.get('track')
        if isinstance(track, int):
            from backend.models import Track as TrackModel
            track = TrackModel.objects.get(pk=track)
        genre = getattr(track, 'genre', '') or ''
        rate = self.get_genre_rate(genre)
        duration = getattr(track, 'duration', 0) or 0
        total = duration * rate
        validated_data['total_earning'] = total
        validated_data['distribution_date'] = timezone.now().date()
        return super().create(validated_data)

class TrackSerializer(serializers.ModelSerializer):
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    streams = StreamDataSerializer(many=True, read_only=True)
    splits = SplitSerializer(many=True, required=False)  # Writable
    # Allow uploading an audio file
    file = serializers.FileField(required=False, allow_null=True)
    royalties = RoyaltyDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Track
        fields = [
            'id', 'title', 'duration', 'genre', 'release_date', 'nft_id',
            'owner', 'owner_email', 'streams', 'splits', 'file', 'royalties', 'payout_amount', 'processed_streams', 'rate_per_stream'
        ]
        read_only_fields = ['id', 'owner_email', 'streams', 'royalties', 'release_date', 'processed_streams']

    def validate_title(self, value):
        """Sanitize track title"""
        if not value:
            raise serializers.ValidationError("Title cannot be empty")
        return InputSanitizer.sanitize_text(value, max_length=200)
    
    def validate_genre(self, value):
        """Sanitize genre"""
        if value:
            return InputSanitizer.sanitize_text(value, max_length=50)
        return value

    def validate(self, data):
        splits = data.get('splits', [])
        if splits:
            total_percentage = sum(s['percentage'] for s in splits)
            if round(total_percentage, 2) != 100.0:
                raise serializers.ValidationError(
                    f"Total percentage must be 100, got {total_percentage}"
                )
        
        # Validate uploaded audio file if provided
        uploaded = data.get('file')
        if uploaded:
            try:
                FileValidator.validate_audio(uploaded)
            except DjangoValidationError as e:
                raise serializers.ValidationError(str(e))
        
        return data

    def create(self, validated_data):
        splits_data = validated_data.pop('splits', [])
        # set release date if not provided
        from datetime import date
        validated_data.setdefault('release_date', date.today())

        track = Track.objects.create(**validated_data)
        for split_data in splits_data:
            Split.objects.create(track=track, **split_data)
        return track
