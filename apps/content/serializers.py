from rest_framework import serializers
from .models import Post, Media
from rest_framework import serializers
from django.utils import timezone
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.contrib.auth import get_user_model

User = get_user_model()

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
    client = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_client=True),
        required=False,
        allow_null=True
    )
    last_edited_by = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = Post
        fields = [
            'id', 'title', 'description', 'scheduled_for', 'status',
            'creator', 'media', 'media_files', 'platforms', 'hashtags', 'client','last_edited_by'
        ]
        read_only_fields = ['id', 'creator', 'media','last_edited_by']

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

        for file in media_files:
            media_instance = Media.objects.create(
                file=file,
                name=file.name,
                creator=self.context['request'].user,
                type=self.determine_file_type(file.name)
            )
            instance.media.add(media_instance)

        return instance

    def determine_file_type(self, file_name):
        if file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            return 'image'
        elif file_name.lower().endswith(('.mp4', '.avi', '.mov', '.webm')):
            return 'video'
        elif file_name.lower().endswith(('.pdf', '.doc', '.docx', '.txt')):
            return 'document'
        return 'other'