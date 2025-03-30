from rest_framework import serializers
from .models import Keyword, Subtopic

class SubtopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subtopic
        fields = ['id', 'title', 'order']

class KeywordSerializer(serializers.ModelSerializer):
    subtopics = SubtopicSerializer(many=True, read_only=True)
    
    class Meta:
        model = Keyword
        fields = ['id', 'keyword', 'main_intent', 'info_needed', 'pain_points', 'created_at', 'subtopics']