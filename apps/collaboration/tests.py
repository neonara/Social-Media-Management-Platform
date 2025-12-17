from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.collaboration.models import ChatRoom, Message

User = get_user_model()


class ChatRoomModelTestCase(TestCase):
    """Test cases for ChatRoom model"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            password="testpass123",
            first_name="User",
            last_name="One",
        )
        self.user2 = User.objects.create_user(
            email="user2@example.com",
            password="testpass123",
            first_name="User",
            last_name="Two",
        )

    def test_create_team_chat_room(self):
        """Test creating a team chat room"""
        chat_room = ChatRoom.objects.create(
            name="Team Room",
            room_type="team",
            created_by=self.user1,
        )
        chat_room.members.add(self.user1, self.user2)
        
        self.assertEqual(chat_room.name, "Team Room")
        self.assertEqual(chat_room.room_type, "team")
        self.assertEqual(chat_room.members.count(), 2)
        self.assertTrue(chat_room.is_active)

    def test_create_direct_message_room(self):
        """Test creating a direct message room"""
        chat_room = ChatRoom.objects.create(
            room_type="direct",
            created_by=self.user1,
        )
        chat_room.members.add(self.user1, self.user2)
        
        self.assertEqual(chat_room.room_type, "direct")
        self.assertEqual(chat_room.members.count(), 2)

    def test_chat_room_string_representation(self):
        """Test chat room string representation"""
        chat_room = ChatRoom.objects.create(
            name="Test Room",
            room_type="team",
            created_by=self.user1,
        )
        self.assertEqual(str(chat_room), "Test Room")

    def test_chat_room_is_active_default(self):
        """Test chat room is_active defaults to True"""
        chat_room = ChatRoom.objects.create(
            name="Active Room",
            created_by=self.user1,
        )
        self.assertTrue(chat_room.is_active)


class MessageModelTestCase(TestCase):
    """Test cases for Message model"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="sender@example.com",
            password="testpass123",
            first_name="Sender",
            last_name="User",
        )
        self.user2 = User.objects.create_user(
            email="receiver@example.com",
            password="testpass123",
        )
        self.chat_room = ChatRoom.objects.create(
            name="Test Room",
            room_type="team",
            created_by=self.user1,
        )
        self.chat_room.members.add(self.user1, self.user2)

    def test_create_message(self):
        """Test creating a message"""
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.user1,
            content="Hello, this is a test message!",
        )
        self.assertEqual(message.content, "Hello, this is a test message!")
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.room, self.chat_room)
        self.assertFalse(message.is_read)

    def test_message_ordering(self):
        """Test messages are ordered by created_at asc"""
        msg1 = Message.objects.create(
            room=self.chat_room,
            sender=self.user1,
            content="First message",
        )
        msg2 = Message.objects.create(
            room=self.chat_room,
            sender=self.user2,
            content="Second message",
        )
        messages = Message.objects.all()
        self.assertEqual(messages[0], msg1)
        self.assertEqual(messages[1], msg2)

    def test_mark_message_as_read(self):
        """Test marking message as read"""
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.user1,
            content="Test message",
        )
        self.assertFalse(message.is_read)
        self.assertIsNone(message.read_at)
        
        message.mark_as_read()
        
        self.assertTrue(message.is_read)
        self.assertIsNotNone(message.read_at)

    def test_message_string_representation(self):
        """Test message string representation"""
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.user1,
            content="This is a test message for string representation",
        )
        self.assertIn("Sender User", str(message))
        self.assertIn("This is a test message", str(message))
