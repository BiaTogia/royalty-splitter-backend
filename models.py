from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from rest_framework import serializers
from decimal import Decimal

# =====================================================
# Role & Lookup tables
# =====================================================
class Role(models.Model):
    role_name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.role_name

class PayoutStatus(models.Model):
    status_name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.status_name

class SeverityLevel(models.Model):
    severity_name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.severity_name

# =====================================================
# Custom User model
# =====================================================
class UserAccountManager(BaseUserManager):
    def create_user(self, email, name, password=None, role=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password, **extra_fields):
        role, _ = Role.objects.get_or_create(role_name="Admin")
        user = self.create_user(email, name, password, role=role, **extra_fields)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user

class UserAccount(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    # Optional profile image for user avatars
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # override groups and permissions to avoid reverse accessor clash
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='useraccount_groups',  # custom related_name
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='useraccount_user_permissions',  # custom related_name
        blank=True
    )

    objects = UserAccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email

# =====================================================
# Track & Stream Data
# =====================================================
class Track(models.Model):
    title = models.CharField(max_length=200)
    duration = models.FloatField(blank=True, null=True)  # duration in minutes
    genre = models.CharField(max_length=50, blank=True, null=True)
    release_date = models.DateField(auto_now_add=True)
    nft_id = models.CharField(max_length=255, blank=True, null=True)
    # Uploaded audio file for the track
    file = models.FileField(upload_to='tracks/', blank=True, null=True)
    owner = models.ForeignKey(UserAccount, on_delete=models.SET_NULL, null=True, related_name="tracks")
    # Uploader-defined total payout amount (in USD)
    payout_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total amount to distribute to collaborators")
    # Total streams already processed (paid out) -> used to compute delta payouts
    processed_streams = models.BigIntegerField(default=0)
    # Optional per-track rate (USD per stream). If null, use global default.
    rate_per_stream = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return self.title

class StreamData(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="streams")
    platform = models.CharField(max_length=100, blank=True, null=True)
    stream_count = models.IntegerField(default=0)
    date_recorded = models.DateField()
    fraud_flag = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['track']),
            models.Index(fields=['date_recorded']),
            models.Index(fields=['platform']),
            models.Index(fields=['fraud_flag']),
        ]

    def __str__(self):
        return f"{self.track.title} - {self.platform} ({self.stream_count})"

# =====================================================
# Royalty & Split
# =====================================================
class Royalty(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="royalties")
    total_earning = models.DecimalField(max_digits=12, decimal_places=2)
    distribution_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.track.title} - {self.total_earning}"

    def get_user_shares(self):
        """Return a dict mapping user email to their royalty share amount.
        The share is calculated as total_earning * (split.percentage / 100).
        """
        shares = {}
        for split in self.track.splits.all():
            share_amount = float(self.total_earning) * (split.percentage / 100.0)
            shares[split.user.email] = round(share_amount, 2)
        return shares

class Split(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="splits")
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name="splits")
    percentage = models.FloatField()

    class Meta:
        unique_together = ("track", "user")
        constraints = [
            models.CheckConstraint(check=models.Q(percentage__gte=0) & models.Q(percentage__lte=100),
                                   name="percentage_between_0_100")
        ]

    def __str__(self):
        return f"{self.user.email} - {self.track.title} ({self.percentage}%)"

# =====================================================
# Wallet & Payout
# =====================================================
class Wallet(models.Model):
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    blockchain_address = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} - {self.balance}"

class Payout(models.Model):
    MIN_PAYOUT_AMOUNT = Decimal('1.0')
    MAX_PAYOUT_AMOUNT = Decimal('999999.99')
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="payouts")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    txn_date = models.DateTimeField(default=timezone.now)
    status = models.ForeignKey(PayoutStatus, on_delete=models.SET_NULL, null=True)
    blockchain_txn_id = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gte=Decimal('1.0')) & models.Q(amount__lte=Decimal('999999.99')),
                name='payout_amount_valid_range'
            )
        ]

    def __str__(self):
        return f"Payout {self.id} - {self.amount} ({self.status})"

# =====================================================
# SIEM Event
# =====================================================
class SIEM_Event(models.Model):
    user = models.ForeignKey(UserAccount, on_delete=models.SET_NULL, null=True)
    event_type = models.CharField(max_length=100)
    severity = models.ForeignKey(SeverityLevel, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.timestamp}"

# =====================================================
# Royalty Serializer
# =====================================================
class RoyaltySerializer(serializers.ModelSerializer):
    track_title = serializers.CharField(source='track.title', read_only=True)
    user_shares = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Royalty
        fields = ['id', 'track', 'track_title', 'total_earning', 'distribution_date', 'user_shares']
        read_only_fields = ['id', 'track_title', 'user_shares']

    def get_user_shares(self, obj):
        return obj.get_user_shares()
