# tasks.py
import asyncio
import logging
from django.core.cache import cache
from celery import shared_task
from .services.generator import ContentGenerator
from .services.optimizer import ContentOptimizer
from .models import BlogContent

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def generate_content_task(self, keyword_id, user_id, target_audience=None, business_info=None, custom_morphemes=None, subtopics=None):
    """
    Celery 태스크: 콘텐츠 생성
    """
    try:
        # 상태 업데이트
        cache.set(
            f"content_generation_{keyword_id}_{user_id}",
            {"status": "running", "progress": 0, "message": "작업 시작 중..."},
            timeout=3600
        )
        
        # 비동기 함수 실행을 위한 이벤트 루프
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            generator = ContentGenerator()
            
            # 진행 상황 업데이트
            cache.set(
                f"content_generation_{keyword_id}_{user_id}",
                {"status": "running", "progress": 25, "message": "연구 자료 수집 중..."},
                timeout=3600
            )
            
            # 비동기 생성 메서드 호출
            content_id = loop.run_until_complete(
                generator.generate_content_async(
                    keyword_id, 
                    user_id, 
                    target_audience, 
                    business_info, 
                    custom_morphemes,
                    subtopics
                )
            )
            
            # 성공적으로 완료
            if content_id:
                cache.set(
                    f"content_generation_{keyword_id}_{user_id}",
                    {
                        "status": "completed",
                        "progress": 100,
                        "content_id": content_id,
                        "message": "콘텐츠가 성공적으로 생성되었습니다."
                    },
                    timeout=3600
                )
                return {"status": "success", "content_id": content_id}
            else:
                cache.set(
                    f"content_generation_{keyword_id}_{user_id}",
                    {
                        "status": "failed",
                        "error": "콘텐츠 생성에 실패했습니다."
                    },
                    timeout=3600
                )
                return {"status": "failed", "error": "콘텐츠 생성 실패"}
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"콘텐츠 생성 태스크 오류: {str(e)}", exc_info=True)
        
        # 재시도
        try:
            self.retry(countdown=60 * self.request.retries)  # 1분, 2분, 3분 간격으로 재시도
        except Exception as retry_error:
            # 모든 재시도 실패
            cache.set(
                f"content_generation_{keyword_id}_{user_id}",
                {
                    "status": "failed",
                    "error": f"콘텐츠 생성 오류: {str(e)}"
                },
                timeout=3600
            )
            
            # 임시 콘텐츠 업데이트
            try:
                temp_content = BlogContent.objects.get(
                    keyword_id=keyword_id,
                    user_id=user_id,
                    title__contains="(생성 중...)"
                )
                temp_content.content = f"콘텐츠 생성 중 오류가 발생했습니다: {str(e)}"
                temp_content.save()
            except Exception:
                pass
                
            return {"status": "failed", "error": str(e)}

@shared_task(bind=True, max_retries=2)
def optimize_content_task(self, content_id):
    """
    Celery 태스크: 콘텐츠 최적화
    """
    try:
        # 상태 업데이트
        cache.set(
            f"content_optimization_{content_id}",
            {"status": "running", "progress": 0, "message": "최적화 시작 중..."},
            timeout=3600
        )
        
        # 최적화 실행
        optimizer = ContentOptimizer()
        result = optimizer.optimize_existing_content_v4(content_id)
        
        # 결과 캐싱
        if result.get('success', False):
            cache.set(
                f"content_optimization_{content_id}",
                {
                    "status": "completed",
                    "message": result.get('message', "최적화 완료"),
                    "content_id": content_id
                },
                timeout=3600
            )
        else:
            cache.set(
                f"content_optimization_{content_id}",
                {
                    "status": "failed",
                    "error": result.get('message', "최적화 실패")
                },
                timeout=3600
            )
            
        return result
        
    except Exception as e:
        logger.error(f"콘텐츠 최적화 태스크 오류: {str(e)}", exc_info=True)
        
        # 재시도
        try:
            self.retry(countdown=30 * self.request.retries)
        except Exception:
            # 모든 재시도 실패
            cache.set(
                f"content_optimization_{content_id}",
                {
                    "status": "failed",
                    "error": f"최적화 오류: {str(e)}"
                },
                timeout=3600
            )
            
            return {"status": "failed", "error": str(e)}