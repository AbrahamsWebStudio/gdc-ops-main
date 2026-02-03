from django.db import migrations


def create_defaults(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    AppSetting = apps.get_model("core", "AppSetting")

    # Default groups
    for name in ["Owner", "Sales", "Ops"]:
        Group.objects.get_or_create(name=name)

    # Default stale_days setting
    AppSetting.objects.get_or_create(
        key="stale_days",
        defaults={"value": "7", "description": "Days since last interaction to mark a lead as stale"},
    )


def remove_defaults(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    AppSetting = apps.get_model("core", "AppSetting")

    Group.objects.filter(name__in=["Owner", "Sales", "Ops"]).delete()
    AppSetting.objects.filter(key="stale_days").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_defaults, remove_defaults),
    ]
