from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TitleSuggestion
from content.models import BlogContent
from .serializers import TitleSuggestionSerializer
from .services.generator import TitleGenerator
from .services.summarizer import ContentSummarizer
import time

class TitleSuggestionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TitleSuggestionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = TitleSuggestion.objects.filter(content__user=self.request.user)
        
        # 필터링
        content_id = self.request.query_params.get('content')
        title_type = self.request.query_params.get('type')
        
        if content_id:
            queryset = queryset.filter(content_id=content_id)
        
        if title_type:
            queryset = queryset.filter(title_type=title_type)
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        content_id = request.data.get('content_id')
        
        if not content_id:
            return Response({"error": "content_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 콘텐츠 확인
            content = BlogContent.objects.get(id=content_id, user=request.user)
            
            # 제목 생성 서비스 초기화
            generator = TitleGenerator(use_openai=False)  # Claude API 사용
            
            # 요청 처리 시간이 오래 걸릴 수 있으니 타임아웃 설정
            # Django REST Framework 기본 응답 시간 제한을 늘린다
            import threading
            
            # 결과 저장 객체
            result = {"success": False, "data": None, "error": None}
            
            # 백그라운드로 제목 생성 시작
            def generate_titles_in_background():
                try:
                    # 제목 생성
                    titles = generator.generate_titles(content.pk)
                    
                    if titles:
                        # 결과 포맷팅
                        formatted_result = {}
                        for title_type, suggestions in titles.items():
                            formatted_result[title_type] = []
                            for suggestion in suggestions:
                                try:
                                    title_obj = TitleSuggestion.objects.get(id=suggestion['id'])
                                    formatted_result[title_type].append(TitleSuggestionSerializer(title_obj).data)
                                except TitleSuggestion.DoesNotExist:
                                    # 처리 도중 삭제된 경우 무시
                                    pass
                                except Exception as e:
                                    print(f"Title serialization error: {str(e)}")
                        
                        result["success"] = True
                        result["data"] = formatted_result
                    else:
                        result["error"] = "제목 생성에 실패했습니다."
                except Exception as e:
                    import traceback
                    print(f"Title generation error: {str(e)}")
                    print(traceback.format_exc())
                    result["error"] = str(e)
            
            # 생성 작업 시작
            thread = threading.Thread(target=generate_titles_in_background)
            thread.daemon = True
            thread.start()
            
            # 최대 30초까지 기다림
            thread.join(timeout=30)
            
            if thread.is_alive():
                # 여전히 실행 중인 경우 백그라운드로 계속 실행되도록 둠
                return Response({
                    "message": "제목 생성이 백그라운드에서 진행 중입니다. 잠시 후 다시 요청해주세요.",
                    "status": "processing",
                    "content_id": content_id
                })
            
            if result["success"]:
                return Response({
                    "message": "제목이 성공적으로 생성되었습니다.",
                    "data": result["data"]
                })
            else:
                return Response({
                    "error": result["error"] or "제목 생성에 실패했습니다."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except BlogContent.DoesNotExist:
            return Response({"error": "Invalid content_id"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """제목 생성 상태 확인"""
        content_id = request.query_params.get('content_id')
        
        if not content_id:
            return Response({"error": "content_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 콘텐츠 확인
            content = BlogContent.objects.get(id=content_id, user=request.user)
            
            # 제목 생성 여부 확인
            titles = TitleSuggestion.objects.filter(content=content)
            
            if titles.exists():
                # 제목 목록을 유형별로 포맷팅
                formatted_result = {}
                for title_type in TitleGenerator.TITLE_TYPES.keys():
                    type_titles = titles.filter(title_type=title_type)
                    formatted_result[title_type] = [
                        TitleSuggestionSerializer(title).data for title in type_titles
                    ]
                
                return Response({
                    "status": "completed",
                    "message": "제목 생성이 완료되었습니다.",
                    "data": formatted_result
                })
            else:
                return Response({
                    "status": "pending",
                    "message": "제목이 아직 생성되지 않았습니다."
                })
                
        except BlogContent.DoesNotExist:
            return Response({"error": "Invalid content_id"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def select(self, request, pk=None):
        title = self.get_object()
        content = title.content
        
        try:
            # 이전에 선택된 제목 해제
            TitleSuggestion.objects.filter(content=content, selected=True).update(selected=False)
            
            # 현재 제목 선택
            title.selected = True
            title.save()
            
            # 콘텐츠 제목 업데이트
            content.title = title.suggestion
            content.save()
            
            return Response({
                "message": "제목이 성공적으로 선택되었습니다.",
                "data": TitleSuggestionSerializer(title).data
            })
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def summarize(self, request):
        content_id = request.data.get('content_id')
        summary_type = request.data.get('summary_type', 'vrew')
        
        if not content_id:
            return Response({"error": "content_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 콘텐츠 확인
            content = BlogContent.objects.get(id=content_id, user=request.user)
            
            # 유효한 요약 유형 확인
            valid_types = ['vrew', 'social', 'bullet']
            if summary_type not in valid_types:
                return Response({"error": "Invalid summary_type"}, status=status.HTTP_400_BAD_REQUEST)
            
            # 요약 생성 서비스 초기화
            summarizer = ContentSummarizer()
            
            # 요약 생성
            summary = summarizer.create_summary(content.pk, summary_type)
            
            return Response({
                "message": "요약이 성공적으로 생성되었습니다.",
                "data": {
                    "summary": summary,
                    "summary_type": summary_type
                }
            })
            
        except BlogContent.DoesNotExist:
            return Response({"error": "Invalid content_id"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)