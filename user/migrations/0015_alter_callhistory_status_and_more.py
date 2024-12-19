# Generated by Django 5.1.1 on 2024-11-20 08:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0014_user_is_active_user_is_staff_user_password"),
    ]

    operations = [
        migrations.AlterField(
            model_name="callhistory",
            name="status",
            field=models.CharField(
                choices=[
                    ("initiated", "Initiated"),
                    ("accepted", "Accepted"),
                    ("ended", "Ended"),
                    ("missed", "Missed"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="callhistory",
            name="zegocloud_call_id",
            field=models.CharField(max_length=255),
        ),
    ]
