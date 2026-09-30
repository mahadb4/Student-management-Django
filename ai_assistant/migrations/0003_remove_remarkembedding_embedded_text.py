from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ai_assistant", "0002_alter_remarkembedding_embedding"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="remarkembedding",
            name="embedded_text",
        ),
    ]
