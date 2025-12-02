from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0007_track_payout_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraccount',
            name='profile_image',
            field=models.ImageField(upload_to='profiles/', null=True, blank=True),
        ),
    ]
