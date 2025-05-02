from rest_framework import serializers
from .models import BlogContent, MorphemeAnalysis
from key_word.serializers import KeywordSerializer

class MorphemeAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = MorphemeAnalysis
        fields = ['id', 'morpheme', 'count', 'is_valid']

class BlogContentSerializer(serializers.ModelSerializer):
    morpheme_analyses = MorphemeAnalysisSerializer(many=True, read_only=True)
    keyword_detail = KeywordSerializer(source='keyword', read_only=True)
    
    class Meta:
        model = BlogContent
        fields = ['id', 'title', 'content', 'mobile_formatted_content', 'references', 
                  'char_count', 'is_optimized', 'created_at', 'updated_at', 
                  'keyword', 'keyword_detail', 'morpheme_analyses']
