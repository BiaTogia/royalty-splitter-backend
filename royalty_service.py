from decimal import Decimal
from django.utils import timezone

from django.db import transaction
from django.db.models import Sum

from .models import Royalty, Split, Wallet, Payout, PayoutStatus, StreamData, Track

ROYALTY_RATE_PER_MINUTE = Decimal("10.0")      # legacy: $10 per minute (unused for streams)
# Default rate per stream (USD)
RATE_PER_STREAM = Decimal("0.003")
PLATFORM_FEE_PERCENT = Decimal("2.0")          # 2% platform fee


def distribute_royalty_for_track(track):
    """
    Uses track.payout_amount as the total earning to distribute.
    Split-lərə görə user-lərə bölür,
    Wallet balanslarını artırır,
    hər user üçün Payout (status=Pending) yaradır,
    eyni zamanda Royalty qeydini yaradır.
    """
    # Use uploader-defined payout amount
    total_earning = Decimal(str(track.payout_amount or 0))
    
    if total_earning <= 0:
        raise ValueError(f"Track payout_amount must be > 0, got {total_earning}")

    # Royalty qeydini yaradaq (audit üçün)
    royalty = Royalty.objects.create(
        track=track,
        total_earning=total_earning,
        distribution_date=timezone.now().date()
    )

    # Status
    pending_status, _ = PayoutStatus.objects.get_or_create(status_name="Pending")

    payouts_created = []

    for split in track.splits.all():
        # Brüt pay
        gross_share = (total_earning * Decimal(str(split.percentage))) / Decimal("100")

        # Platform fee çıxıldıqdan sonra
        net_share = gross_share * (Decimal("100") - PLATFORM_FEE_PERCENT) / Decimal("100")

        # Wallet tap / yarat
        wallet, _ = Wallet.objects.get_or_create(user=split.user)
        wallet.balance += net_share
        wallet.last_updated = timezone.now()
        wallet.save()

        # Pending payout yarat
        payout = Payout.objects.create(
            wallet=wallet,
            amount=net_share,
            status=pending_status,
            txn_date=timezone.now()
        )
        payouts_created.append(payout)

    return {
        "royalty_id": royalty.id,
        "track_id": track.id,
        "total_earning": total_earning,
        "payouts_count": len(payouts_created),
    }


def distribute_royalty_from_streams(track, rate_per_stream: Decimal = None):
    """
    Distribute royalties for the new (unprocessed) streams of a track.

    This function computes the delta between total stream_count (sum of StreamData)
    and `track.processed_streams`, converts the delta to USD using `rate_per_stream`
    (or default RATE_PER_STREAM), then distributes the earnings across splits.

    The function updates `track.processed_streams` to avoid double-paying streams.
    """
    rate = rate_per_stream or RATE_PER_STREAM

    # Sum total streams (exclude fraud flagged rows)
    agg = StreamData.objects.filter(track=track, fraud_flag=False).aggregate(total=Sum('stream_count'))
    total_streams = int(agg.get('total') or 0)

    processed = int(track.processed_streams or 0)
    delta_streams = total_streams - processed
    if delta_streams <= 0:
        return {
            "royalty_id": None,
            "track_id": track.id,
            "total_earning": Decimal("0.00"),
            "payouts_count": 0,
            "message": "No new streams to distribute",
        }

    total_earning = (Decimal(delta_streams) * Decimal(str(rate))).quantize(Decimal('0.01'))

    if total_earning <= Decimal("0.00"):
        return {
            "royalty_id": None,
            "track_id": track.id,
            "total_earning": Decimal("0.00"),
            "payouts_count": 0,
            "message": "No earnings computed from streams",
        }

    with transaction.atomic():
        royalty = Royalty.objects.create(
            track=track,
            total_earning=total_earning,
            distribution_date=timezone.now().date()
        )

        pending_status, _ = PayoutStatus.objects.get_or_create(status_name="Pending")

        payouts_created = []

        for split in track.splits.all():
            gross_share = (total_earning * Decimal(str(split.percentage))) / Decimal("100")
            net_share = (gross_share * (Decimal("100") - PLATFORM_FEE_PERCENT) / Decimal("100")).quantize(Decimal('0.01'))

            wallet, _ = Wallet.objects.get_or_create(user=split.user)
            # Ensure wallet.balance is Decimal
            wallet.balance = (wallet.balance or Decimal('0.00')) + net_share
            wallet.last_updated = timezone.now()
            wallet.save()

            payout = Payout.objects.create(
                wallet=wallet,
                amount=net_share,
                status=pending_status,
                txn_date=timezone.now()
            )
            payouts_created.append(payout)

        # Mark processed streams to avoid double-pay
        track.processed_streams = total_streams
        track.save(update_fields=['processed_streams'])

    return {
        "royalty_id": royalty.id,
        "track_id": track.id,
        "total_earning": total_earning,
        "payouts_count": len(payouts_created),
    }
