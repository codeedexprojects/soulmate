# Generated by Django 5.1.1 on 2024-11-20 08:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0015_alter_callhistory_status_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="callhistory",
            name="zegocloud_call_id",
            field=models.CharField(default="", max_length=255),
        ),
    ]
