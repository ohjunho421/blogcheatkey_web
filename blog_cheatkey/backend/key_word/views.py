#key_word/views.py
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
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"키워드 분석 시작: {keyword.keyword}")
            
            try:
                analyzer = KeywordAnalyzer()
                logger.info("KeywordAnalyzer 초기화 성공")
            except Exception as init_error:
                logger.error(f"KeywordAnalyzer 초기화 실패: {str(init_error)}")
                return Response({"error": f"분석기 초기화 실패: {str(init_error)}"}, 
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 분석 수행
            try:
                analysis_result = analyzer.analyze_keyword(keyword.keyword)
                logger.info(f"키워드 분석 완료: {analysis_result}")
            except Exception as analysis_error:
                logger.error(f"키워드 분석 실패: {str(analysis_error)}")
                return Response({"error": f"키워드 분석 실패: {str(analysis_error)}"}, 
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 분석 결과 저장
            try:
                keyword.main_intent = analysis_result.get('main_intent', '')
                keyword.info_needed = analysis_result.get('info_needed', [])
                keyword.pain_points = analysis_result.get('pain_points', [])
                keyword.save()
                logger.info("키워드 분석 결과 저장 완료")
            except Exception as save_error:
                logger.error(f"키워드 분석 결과 저장 실패: {str(save_error)}")
                return Response({"error": f"분석 결과 저장 실패: {str(save_error)}"}, 
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 소제목 추천
            try:
                subtopics = analyzer.suggest_subtopics(keyword.keyword)
                logger.info(f"소제목 추천 완료: {subtopics}")
                
                for i, subtopic in enumerate(subtopics):
                    Subtopic.objects.create(
                        keyword=keyword,
                        title=subtopic,
                        order=i
                    )
                logger.info("소제목 데이터베이스 저장 완료")
            except Exception as subtopic_error:
                logger.error(f"소제목 추천 또는 저장 실패: {str(subtopic_error)}")
                return Response({"error": f"소제목 처리 실패: {str(subtopic_error)}"}, 
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                "message": "키워드 분석이 완료되었습니다.",
                "data": KeywordSerializer(keyword).data
            })
            
        except Exception as e:
            import traceback
            logger.error(f"키워드 분석 중 예외 발생: {str(e)}\n{traceback.format_exc()}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def update_intent(self, request, pk=None):
        """
        키워드의 검색 의도, 필요 정보, pain points 등을 업데이트
        """
        keyword = self.get_object()
        
        try:
            data = request.data
            
            # 검색 의도 업데이트
            if 'main_intent' in data:
                keyword.main_intent = data['main_intent']
            
            # 필요 정보 업데이트
            if 'info_needed' in data:
                keyword.info_needed = data['info_needed']
                
            # pain points 업데이트
            if 'pain_points' in data:
                keyword.pain_points = data['pain_points']
                
            keyword.save()
            
            return Response({
                "message": "키워드 분석 정보가 성공적으로 업데이트되었습니다.",
                "data": KeywordSerializer(keyword).data
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def update_subtopics(self, request, pk=None):
        """
        키워드의 소제목 목록을 업데이트
        """
        keyword = self.get_object()
        
        try:
            data = request.data
            if 'subtopics' not in data or not isinstance(data['subtopics'], list):
                return Response({"error": "소제목 목록이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
            
            # 기존 소제목 삭제
            keyword.subtopics.all().delete()
            
            # 새 소제목 추가
            for i, title in enumerate(data['subtopics']):
                if isinstance(title, dict) and 'title' in title:
                    title = title['title']
                    
                if not isinstance(title, str):
                    continue
                    
                Subtopic.objects.create(
                    keyword=keyword,
                    title=title,
                    order=i
                )
            
            return Response({
                "message": "소제목이 성공적으로 업데이트되었습니다.",
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
        
    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """
        소제목 순서 변경
        """
        try:
            data = request.data
            if 'subtopics' not in data or not isinstance(data['subtopics'], list):
                return Response({"error": "소제목 목록이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
                
            # 소제목 순서 업데이트
            for i, item in enumerate(data['subtopics']):
                if 'id' not in item:
                    continue
                    
                subtopic = Subtopic.objects.filter(
                    id=item['id'], 
                    keyword__user=request.user
                ).first()
                
                if subtopic:
                    subtopic.order = i
                    if 'title' in item:
                        subtopic.title = item['title']
                    subtopic.save()
            
            return Response({"message": "소제목 순서가 업데이트되었습니다."})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)