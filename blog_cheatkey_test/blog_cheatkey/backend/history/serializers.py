from rest_framework import serializers
from .models import ContentHistory

class ContentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentHistory
        fields = ['id', 'title', 'content', 'keywords', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']