from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None  # Remove the username field
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    first_name = models.CharField(max_length=25, blank=True, null=True)
    last_name = models.CharField(max_length=25, blank=True, null=True)
    user_image = models.FileField(upload_to="accounts/images/", blank=True, null=True)

    is_verified = models.BooleanField(default=True)
    is_administrator = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False)
    is_community_manager = models.BooleanField(default=False)
    is_client = models.BooleanField(default=False)
    is_superadministrator = models.BooleanField(default=False)

    assigned_moderator = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients_assigned",
        limit_choices_to={"is_moderator": True},
        help_text="The Moderator assigned to this Client",
    )

    assigned_communitymanagers = models.ManyToManyField(
        "self",
        blank=True,
        related_name="moderators",
        limit_choices_to={"is_community_manager": True},
        symmetrical=False,
        help_text="The Community Managers assigned to this Moderator",
    )

    assigned_communitymanagerstoclient = models.ManyToManyField(
        "self",
        blank=True,
        related_name="clients",
        limit_choices_to={"is_community_manager": True},
        symmetrical=False,
        help_text="The Community Managers assigned to this Client",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        This method is cached for better performance.
        """
        cache_key = f"user_fullname:{self.id}"
        cached_name = cache.get(cache_key)

        if cached_name is not None:
            return cached_name

        full_name = f"{self.first_name} {self.last_name}".strip()
        cache.set(cache_key, full_name, 3600)  # Cache for 1 hour
        return full_name

    def get_meta_data(self):
        """
        Return user's metadata including permissions and profile info.
        This method is cached for better performance.
        """
        cache_key = f"user_meta:{self.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return cached_data

        meta_data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_staff": self.is_staff,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "is_administrator": self.is_administrator,
            "is_moderator": self.is_moderator,
            "is_community_manager": self.is_community_manager,
            "is_client": self.is_client,
            "is_supplier": self.is_supplier,
            # Add other relevant fields
        }

        try:
            profile = self.profile
            meta_data.update(
                {
                    "profile_image": profile.image.url if profile.image else None,
                    "bio": profile.bio,
                    # Add other profile fields
                }
            )
        except:
            pass

        cache.set(cache_key, meta_data, 3600)  # Cache for 1 hour
        return meta_data

    def clear_cache(self):
        """Clear all cached data for this user"""
        cache.delete(f"user_meta:{self.id}")
        cache.delete(f"user_fullname:{self.id}")
        cache.delete(f"user_notifications:{self.id}")
        cache.delete(f"user_unread_count:{self.id}")


@receiver(post_save, sender=User)
def clear_user_cache(sender, instance, **kwargs):
    """Clear user cache when user model is updated"""
    instance.clear_cache()
