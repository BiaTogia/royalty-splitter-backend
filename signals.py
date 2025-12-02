from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserAccount, Wallet, Track
from .royalty_service import distribute_royalty_for_track


@receiver(post_save, sender=UserAccount)
def create_user_wallet(sender, instance, created, **kwargs):
    """
    Yeni UserAccount yaradılan kimi avtomatik wallet yaradır.
    Əgər artıq varsa, heç nə etmir.
    """
    if created:
        Wallet.objects.get_or_create(user=instance)


@receiver(post_save, sender=Track)
def auto_distribute_royalties(sender, instance, created, **kwargs):
    """
    Track yaradıldıqdan sonra və splits tapılmışsa,
    avtomatik olaraq royalty-ni bölüb payouts yaradır.
    """
    if created:
        # Track-in splits-ləri var-mı yoxla
        if instance.splits.exists():
            try:
                distribute_royalty_for_track(instance)
            except Exception as e:
                # Log error but don't break track creation
                print(f"Error distributing royalties for track {instance.id}: {e}")


# If splits are added after the track is created (frontend often creates track first,
# then posts splits), listen for Split creation and distribute royalties if not done yet.
from .models import Split, Royalty


@receiver(post_save, sender=Split)
def distribute_on_split_creation(sender, instance, created, **kwargs):
    try:
        if not created:
            return

        track = instance.track
        if not track:
            return

        # If royalties already exist for this track, don't distribute again
        if Royalty.objects.filter(track=track).exists():
            return

        # Only distribute when track has at least one split (it does now)
        if track.splits.exists():
            try:
                distribute_royalty_for_track(track)
            except Exception as e:
                print(f"Error distributing royalties on split create for track {track.id}: {e}")
    except Exception as e:
        print(f"Error in distribute_on_split_creation signal: {e}")
