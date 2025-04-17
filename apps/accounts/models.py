from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

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
    

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    first_name = models.CharField(max_length=25, blank=True, null=True)
    last_name = models.CharField(max_length=25, blank=True, null=True)
    user_image = models.ImageField(upload_to='accounts/images/', blank=True, null=True)

    is_verified = models.BooleanField(default=True)
    is_administrator = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False)
    is_community_manager = models.BooleanField(default=False)
    is_client = models.BooleanField(default=False)

    assigned_moderator = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients_assigned',
        limit_choices_to={'is_moderator': True},
        help_text="The Moderator assigned to this Client"
    )
    assigned_communitymanagers = models.ManyToManyField(
        'self',
        blank=True,
        related_name='assigned_moderators',
        limit_choices_to={'is_community_manager': True},
        symmetrical=False
    )

    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    



    objects = CustomUserManager()

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()
