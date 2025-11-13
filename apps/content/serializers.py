from rest_framework import serializers
from .models import Post, Media
from apps.accounts.models import User

class UserSerializer(serializers.ModelSerializer):
    """Serializer for User objects."""

    def get(self, instance):
        """Return serialized data for a single user instance."""
        return self.to_representation(instance)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'phone_number', 'is_verified',
            'is_administrator', 'is_moderator', 'is_community_manager',
            'is_client', 'is_superadministrator', 'user_image'
        ]
        read_only_fields = ['id', 'email', 'full_name']
        
#media
class MediaSerializer(serializers.ModelSerializer):
    file_type = serializers.CharField(source='type', read_only=True)
    
    class Meta:
        model = Media
        fields = ['id', 'file', 'name', 'uploaded_at', 'file_type', 'creator']
        read_only_fields = ['id', 'uploaded_at', 'creator', 'file_type']
        
    def get_file(self, obj):
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

#post
class PostSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    client = UserSerializer(read_only=True)
    media = MediaSerializer(many=True, required=False, read_only=True)
    media_files = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False, use_url=False),
        write_only=True,
        required=False,
        default=list
    )
    hashtags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False,
        default=list
    )
    last_edited_by = serializers.StringRelatedField(read_only=True)
    feedback_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'description', 'scheduled_for', 'status', 'created_at', 'updated_at',
            'creator', 'media', 'media_files', 'platforms', 'hashtags', 'client',
            'last_edited_by', 'feedback', 'feedback_by', 'feedback_at',
            'client_approved_at', 'client_rejected_at', 'moderator_validated_at', 
            'moderator_rejected_at', 'published_at', 'is_client_approved', 'is_moderator_validated'
        ]
        read_only_fields = [
            'id', 'creator','client', 'media','last_edited_by', 'feedback_by', 'feedback_at',
            'client_approved_at', 'client_rejected_at', 'moderator_validated_at', 
            'moderator_rejected_at', 'published_at', 'is_client_approved', 'is_moderator_validated'
        ]

    def create(self, validated_data):
        media_files = validated_data.pop('media_files', [])
        hashtags = validated_data.pop('hashtags', [])
        if hashtags:
            hashtag_string = ' '.join([f"#{tag}" for tag in hashtags]) 
            validated_data['description'] = f"{validated_data.get('description', '').strip()}\n\n{hashtag_string}"
        validated_data['creator'] = self.context['request'].user #creator houwa l logged user

        post = Post.objects.create(**validated_data)

        for file in media_files:
            media_instance = Media.objects.create(
                file=file,
                name=file.name,
                creator=self.context['request'].user,
                type=self.determine_file_type(file.name)
            )
            post.media.add(media_instance)

        return post

    def update(self, instance, validated_data):
        media_files = validated_data.pop('media_files', [])
        hashtags = validated_data.pop('hashtags', [])

        # Get existing media IDs from context (passed by view during edit)
        existing_media_ids = self.context.get('existing_media', [])

        #ll hashtag
        if hashtags:
            hashtag_string = ' '.join([f"#{tag}" for tag in hashtags])  
            validated_data['description'] = f"{validated_data.get('description', instance.description).strip()}\n\n{hashtag_string}"

        #win lupdate
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.scheduled_for = validated_data.get('scheduled_for', instance.scheduled_for)
        instance.status = validated_data.get('status', instance.status)
        instance.platforms = validated_data.get('platforms', instance.platforms)
        instance.save()

        # Clear existing media and rebuild with only the media user wants to keep
        instance.media.clear()
        
        # Add back existing media that user wants to keep
        if existing_media_ids:
            from .models import Media
            for media_id in existing_media_ids:
                try:
                    media_instance = Media.objects.get(id=int(media_id))
                    instance.media.add(media_instance)
                except (Media.DoesNotExist, ValueError):
                    pass  # Skip if media doesn't exist or ID is invalid

        # Add new media files
        for file in media_files:
            media_instance = Media.objects.create(
                file=file,
                name=file.name,
                creator=self.context['request'].user,
                type=self.determine_file_type(file.name)
            )
            instance.media.add(media_instance)

        return instance

    def save(self, **kwargs):
        # Extract last_edited_by from kwargs if present
        last_edited_by = kwargs.pop('last_edited_by', None)
        
        # Call parent save method
        instance = super().save(**kwargs)
        
        # Set last_edited_by if provided and save again
        if last_edited_by is not None:
            instance.last_edited_by = last_edited_by
            instance.save(update_fields=['last_edited_by'])
            
        return instance

    def determine_file_type(self, file_name):
        if file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            return 'image'
        elif file_name.lower().endswith(('.mp4', '.avi', '.mov', '.webm')):
            return 'video'
        elif file_name.lower().endswith(('.pdf', '.doc', '.docx', '.txt')):
            return 'document'
        return 'other'