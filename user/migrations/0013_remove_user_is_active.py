# Generated by Django 5.1.1 on 2024-11-08 04:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0012_user_is_active_referralcode_referralhistory"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="is_active",
        ),
    ]
