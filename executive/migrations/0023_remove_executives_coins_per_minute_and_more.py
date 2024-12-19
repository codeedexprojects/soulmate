# Generated by Django 5.1.1 on 2024-11-21 09:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("executive", "0022_alter_executivecallhistory_zegocloud_call_id"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="executives",
            name="coins_per_minute",
        ),
        migrations.AddField(
            model_name="executives",
            name="coins_per_second",
            field=models.FloatField(default=3),
        ),
        migrations.AddField(
            model_name="executives",
            name="on_call",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="executivecallhistory",
            name="zegocloud_call_id",
            field=models.CharField(max_length=255),
        ),
    ]
