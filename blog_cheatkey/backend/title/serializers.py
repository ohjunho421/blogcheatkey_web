from rest_framework import serializers
from .models import TitleSuggestion
from content.serializers import BlogContentSerializer

class TitleSuggestionSerializer(serializers.ModelSerializer):
    content_detail = BlogContentSerializer(source='content', read_only=True)
    
    class Meta:
        model = TitleSuggestion
        fields = ['id', 'title_type', 'suggestion', 'selected', 'created_at', 'content', 'content_detail']
