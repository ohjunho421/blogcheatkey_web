from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Keyword, Subtopic
from .serializers import KeywordSerializer, SubtopicSerializer
from .services.analyzer import KeywordAnalyzer

class KeywordViewSet(viewsets.ModelViewSet):
    serializer_class = KeywordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Keyword.objects.filter(user=self.request.user).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        keyword = self.get_object()
        
        # 이미 분석 결과가 있는지 확인
        if keyword.main_intent:
            return Response({"message": "이미 분석된 키워드입니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 키워드 분석 서비스 초기화
            analyzer = KeywordAnalyzer()
            
            # 분석 수행
            analysis_result = analyzer.analyze_keyword(keyword.keyword)
            
            # 분석 결과 저장
            keyword.main_intent = analysis_result.get('main_intent', '')
            keyword.info_needed = analysis_result.get('info_needed', [])
            keyword.pain_points = analysis_result.get('pain_points', [])
            keyword.save()
            
            # 소제목 추천
            subtopics = analyzer.suggest_subtopics(keyword.keyword)
            for i, subtopic in enumerate(subtopics):
                Subtopic.objects.create(
                    keyword=keyword,
                    title=subtopic,
                    order=i
                )
            
            return Response({
                "message": "키워드 분석이 완료되었습니다.",
                "data": KeywordSerializer(keyword).data
            })
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SubtopicViewSet(viewsets.ModelViewSet):
    serializer_class = SubtopicSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Subtopic.objects.filter(keyword__user=self.request.user)
    
    def perform_create(self, serializer):
        keyword_id = self.request.data.get('keyword')
        keyword = Keyword.objects.get(id=keyword_id, user=self.request.user)
        
        # 순서 설정 (마지막 순서 + 1)
        last_order = keyword.subtopics.order_by('-order').first()
        order = (last_order.order + 1) if last_order else 0
        
        serializer.save(keyword=keyword, order=order)
