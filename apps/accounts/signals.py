# apps/accounts/signals.py
import logging
from django.db import models
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from apps.accounts.models import User

logger = logging.getLogger(__name__)


def create_dm_room(user1, user2):
    """
    Create a direct message room between two users if it doesn't exist.
    Returns the room if created or already exists.
    """
    from apps.collaboration.models import ChatRoom
    
    if not user1 or not user2 or user1 == user2:
        return None
    
    # Check if DM already exists between these users
    existing_room = ChatRoom.objects.filter(
        room_type="direct",
        members=user1
    ).filter(members=user2).first()
    
    if existing_room:
        logger.info(f"DM room already exists between {user1.email} and {user2.email}")
        return existing_room
    
    # Create new DM room
    try:
        room = ChatRoom.objects.create(
            room_type="direct",
            created_by=user1
        )
        room.members.add(user1, user2)
        logger.info(f"Created DM room between {user1.email} and {user2.email}")
        return room
    except Exception as e:
        logger.error(f"Error creating DM room: {e}")
        return None


@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    """
    When a new user is created:
    1. Create DM with all admins
    2. Create DM with assigned moderator (if client)
    """
    if created:
        logger.info(f"New user created: {instance.email}")
        
        # Create DM with all administrators
        admins = User.objects.filter(
            is_active=True
        ).filter(
            models.Q(is_administrator=True)
        )
        
        for admin in admins:
            if admin != instance:
                create_dm_room(instance, admin)
        
        # If client and has assigned moderator, create DM
        if instance.is_client and instance.assigned_moderator:
            create_dm_room(instance, instance.assigned_moderator)


@receiver(post_save, sender=User)
def handle_moderator_assignment(sender, instance, created, **kwargs):
    """
    When a client's assigned_moderator is updated, create DM room.
    """
    if not created and instance.is_client:
        # Check if assigned_moderator field was updated
        if instance.assigned_moderator:
            create_dm_room(instance, instance.assigned_moderator)


@receiver(m2m_changed, sender=User.assigned_communitymanagers.through)
def handle_cm_to_moderator_assignment(sender, instance, action, pk_set, **kwargs):
    """
    When CMs are assigned to a Moderator, create DM rooms.
    """
    if action == "post_add" and pk_set:
        for cm_id in pk_set:
            try:
                cm = User.objects.get(pk=cm_id)
                create_dm_room(instance, cm)
            except User.DoesNotExist:
                logger.error(f"CM with id {cm_id} not found")


@receiver(m2m_changed, sender=User.assigned_communitymanagerstoclient.through)
def handle_cm_to_client_assignment(sender, instance, action, pk_set, **kwargs):
    """
    When CMs are assigned to a Client, create DM rooms.
    """
    if action == "post_add" and pk_set:
        for cm_id in pk_set:
            try:
                cm = User.objects.get(pk=cm_id)
                create_dm_room(instance, cm)
            except User.DoesNotExist:
                logger.error(f"CM with id {cm_id} not found")
