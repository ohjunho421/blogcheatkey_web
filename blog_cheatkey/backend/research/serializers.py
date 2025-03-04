from rest_framework import serializers
from .models import ResearchSource, StatisticData

class StatisticDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatisticData
        fields = ['id', 'value', 'context', 'pattern_type']

class ResearchSourceSerializer(serializers.ModelSerializer):
    statistics = StatisticDataSerializer(many=True, read_only=True)
    
    class Meta:
        model = ResearchSource
        fields = ['id', 'source_type', 'title', 'url', 'snippet', 'author', 'published_date', 'created_at', 'statistics']

