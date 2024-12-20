# Generated by Django 5.1.1 on 2024-10-19 09:55

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("executive", "0009_executivecallhistory_zegocloud_call_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="RevenueTarget",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "target_revenue",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                ("target_talktime", models.DurationField()),
                ("date", models.DateField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.AlterField(
            model_name="executives",
            name="is_banned",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="executives",
            name="is_suspended",
            field=models.BooleanField(default=False),
        ),
    ]
