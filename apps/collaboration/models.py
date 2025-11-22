from django.db import models
from django.conf import settings
from django.utils import timezone


class ChatRoom(models.Model):
    ROOM_TYPES = [
        ("team", "Team Chat"),
        ("direct", "Direct Message"),
    ]

    name = models.CharField(max_length=255, blank=True, null=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default="team")
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="chat_rooms"
    )
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_chat_rooms",
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.name:
            return self.name
        elif self.room_type == "direct":
            member_names = [
                user.get_full_name() or user.email for user in self.members.all()
            ]
            return f"DM: {', '.join(member_names)}"
        else:
            return f"Team Chat {self.id}"

    class Meta:
        ordering = ["-created_at"]


class Message(models.Model):
    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"{self.sender.get_full_name() or self.sender.email}: {self.content[:50]}"
        )

    class Meta:
        ordering = ["created_at"]

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])
