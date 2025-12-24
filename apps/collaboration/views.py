from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer, ChatRoomCreateSerializer
from rest_framework.views import APIView


class ChatRoomViewSet(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ChatRoom.objects.filter(
            members=self.request.user, is_active=True
        ).prefetch_related("members", "messages")

    def get_serializer_class(self):
        if self.action == "create":
            return ChatRoomCreateSerializer
        return ChatRoomSerializer

    def perform_create(self, serializer):
        # Ensure current user is added to members
        instance = serializer.save()
        instance.members.add(self.request.user)
        return instance

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # For direct messages, check if a room already exists between the two users
        if serializer.validated_data.get("room_type") == "direct":
            members = serializer.validated_data.get("members", [])
            if len(members) == 1:  # Should be one other user
                other_user = members[0]
                # Check for existing direct room between current user and other_user
                existing_room = (
                    ChatRoom.objects.filter(
                        room_type="direct", members=request.user, is_active=True
                    )
                    .filter(members=other_user)
                    .annotate(member_count=Count("members"))
                    .filter(member_count=2)
                    .first()
                )

                if existing_room:
                    # Return the existing room instead of creating a new one
                    serializer = self.get_serializer(existing_room)
                    return Response(serializer.data, status=status.HTTP_200_OK)

        # Proceed with normal creation
        return super().create(request, *args, **kwargs)


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Message.objects.filter(
                room__members=self.request.user, room__is_active=True
            )
            .select_related("sender", "room")
            .order_by("-created_at")
        )


class SendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        room_id = request.data.get("room_id")
        content = request.data.get("content")

        if not room_id:
            return Response(
                {"error": "room_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not content:
            return Response(
                {"error": "Message content is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            room = ChatRoom.objects.get(
                id=room_id, members=request.user, is_active=True
            )
        except ChatRoom.DoesNotExist:
            return Response(
                {"error": "Chat room not found or access denied"},
                status=status.HTTP_404_NOT_FOUND,
            )

        message = Message.objects.create(
            room=room, sender=request.user, content=content
        )

        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class GetRoomMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_id):
        try:
            room = ChatRoom.objects.get(
                id=room_id, members=request.user, is_active=True
            )
        except ChatRoom.DoesNotExist:
            return Response(
                {"error": "Chat room not found or access denied"},
                status=status.HTTP_404_NOT_FOUND,
            )

        messages = room.messages.all().order_by("created_at")

        # Mark messages as read for current user
        messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)


class GetDirectMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        other_user_id = request.query_params.get("user_id")
        if not other_user_id:
            return Response(
                {"error": "user_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Find existing direct message room between users
            room = (
                ChatRoom.objects.filter(
                    room_type="direct", members=request.user, is_active=True
                )
                .filter(members=other_user_id)
                .annotate(member_count=Count("members"))
                .filter(member_count=2)
                .first()
            )

            if room:
                serializer = ChatRoomSerializer(room)
                return Response(serializer.data)
            else:
                return Response(
                    {"error": "No direct message room found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
