from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("facebook_integration", "0008_publishedpost_image_file_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="aiconfiguration",
            name="provider",
            field=models.CharField(
                choices=[("openai", "OpenAI"), ("gemini", "Google Gemini")],
                default="openai",
                max_length=20,
                verbose_name="Provedor",
            ),
        ),
    ]
