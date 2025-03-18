from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=False)
    is_administrator = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False)
    is_community_manager = models.BooleanField(default=False)
    is_client = models.BooleanField(default=False)

    username = None  
    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = []  

    def __str__(self):
        return self.email
