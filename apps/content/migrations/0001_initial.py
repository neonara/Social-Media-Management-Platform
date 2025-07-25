# Generated by Django 4.2 on 2025-06-24 11:36

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("social_media", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Media",
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
                ("file", models.FileField(upload_to="media/")),
                ("name", models.CharField(blank=True, max_length=255)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("image", "Image"),
                            ("video", "Video"),
                            ("document", "Document"),
                        ],
                        default="image",
                        max_length=10,
                    ),
                ),
                ("uploaded_at", models.DateTimeField(auto_now_add=True, null=True)),
                (
                    "creator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Post",
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
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("pending", "Pending"),
                            ("rejected", "Rejected"),
                            ("scheduled", "Scheduled"),
                            ("published", "Published"),
                            ("failed", "Failed"),
                        ],
                        default="draft",
                        max_length=10,
                    ),
                ),
                ("platforms", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "client",
                    models.ForeignKey(
                        blank=True,
                        limit_choices_to={"is_client": True},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="client_posts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="posts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "last_edited_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="The user who last edited this post",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="last_edited_posts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "media",
                    models.ManyToManyField(
                        blank=True, related_name="posts", to="content.media"
                    ),
                ),
                (
                    "platform_page",
                    models.ForeignKey(
                        blank=True,
                        help_text="The exact Page or Account where this post is scheduled",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="posts",
                        to="social_media.socialpage",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
