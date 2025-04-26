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
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email=email, password=password, **extra_fields)

class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    full_name = models.CharField(max_length=255, blank=True, null=True)


    is_verified = models.BooleanField(default=False)
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
    'self',  # Refers to the same User model
    blank=True,
    related_name='assigned_moderators',
    limit_choices_to={'is_community_manager': True},
    symmetrical=False  
    )
    assigned_communitymanagerstoclient = models.ManyToManyField(
    'self',
    blank=True,
    symmetrical=False,
    related_name='assigned_moderator_for_client',
    limit_choices_to={'is_cm': True})


    username = None

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        
        if self.first_name is not None and self.last_name is not None:
            if self.first_name != self._meta.get_field('first_name').value_from_object(self) or \
               self.last_name != self._meta.get_field('last_name').value_from_object(self):
                self.full_name = f"{self.first_name} {self.last_name}".strip()
        super().save(*args, **kwargs)