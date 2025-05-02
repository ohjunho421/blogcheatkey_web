# title/services/summarizer.py
import logging
from anthropic import Anthropic
from django.conf import settings
from content.models import BlogContent

logger = logging.getLogger(__name__)

class ContentSummarizer:
    """
    블로그 콘텐츠 요약 서비스
    """
    
    def __init__(self):
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        self.client = Anthropic(api_key=self.anthropic_api_key)
        self.model = "claude-3-7-sonnet-20250219"
    
    def create_summary(self, content_id, summary_type='vrew'):
        """
        블로그 콘텐츠 요약 생성
        
        Args:
            content_id (int): BlogContent 모델의 ID
            summary_type (str): 요약 유형 (vrew, social, bullet)
            
        Returns:
            str: 생성된 요약
        """
        try:
            # 블로그 콘텐츠 정보 가져오기
            blog_content = BlogContent.objects.get(id=content_id)
            content = blog_content.content
            keyword = blog_content.keyword.keyword
            
            # 요약 유형에 따른 프롬프트 설정
            if summary_type == 'vrew':
                prompt = self._create_vrew_prompt(content, keyword)
            elif summary_type == 'social':
                prompt = self._create_social_prompt(content, keyword)
            elif summary_type == 'bullet':
                prompt = self._create_bullet_prompt(content, keyword)
            else:
                prompt = self._create_vrew_prompt(content, keyword)
            
            # 요약 생성
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text
            
        except BlogContent.DoesNotExist:
            logger.error(f"블로그 콘텐츠 ID {content_id}를 찾을 수 없습니다.")
            return None
        except Exception as e:
            logger.error(f"콘텐츠 요약 중 오류: {str(e)}")
            return None
    
    def _create_vrew_prompt(self, content, keyword):
        """
        Vrew 스타일 영상 스크립트 요약 프롬프트 생성
        """
        return f"""
        다음 블로그 콘텐츠를 Vrew와 같은 영상 제작 도구에서 사용할 수 있는 간결한 스크립트로 변환해주세요:
        
        키워드: {keyword}
        
        콘텐츠:
        {content[:2000]}...
        
        다음 조건을 준수해주세요:
        1. 전체 길이는 300-500자 내외로 요약
        2. 각 문장은 짧고 명확하게 (10-15자 내외)
        3. 한 문장 = 한 화면에 표시될 내용으로 가정
        4. 자연스러운 말투로 작성 (예: "~합니다", "~해요")
        5. 핵심 내용과 통계 데이터 위주로 요약
        6. 각 문장은 새로운 줄에 작성
        
        스크립트 형식:
        [문장1]
        [문장2]
        [문장3]
        ...
        
        결과물은 영상 제작 시 바로 사용할 수 있는 형태로 제공해주세요.
        """
    
    def _create_social_prompt(self, content, keyword):
        """
        소셜 미디어용 요약 프롬프트 생성
        """
        return f"""
        다음 블로그 콘텐츠를 소셜 미디어(인스타그램, 페이스북 등)에 공유하기 좋은 형태로 요약해주세요:
        
        키워드: {keyword}
        
        콘텐츠:
        {content[:2000]}...
        
        다음 조건을 준수해주세요:
        1. 전체 길이는 200-300자 내외
        2. 흥미로운 통계나 인사이트로 시작
        3. 이모지 적절히 활용
        4. 해시태그 5-7개 포함 (예: #키워드 #관련주제)
        5. CTA(Call to Action) 포함 (예: "자세한 내용은 블로그에서 확인하세요")
        
        요약 형식:
        [흥미로운 시작]
        
        [핵심 포인트 1-2개]
        
        [CTA]
        
        [해시태그]
        """
    
    def _create_bullet_prompt(self, content, keyword):
        """
        글머리 기호 요약 프롬프트 생성
        """
        return f"""
        다음 블로그 콘텐츠를 글머리 기호(bullet points)로 요약해주세요:
        
        키워드: {keyword}
        
        콘텐츠:
        {content[:2000]}...
        
        다음 조건을 준수해주세요:
        1. 제목과 간략한 소개 문장 포함
        2. 핵심 포인트 5-7개를 글머리 기호(•)로 나열
        3. 각 포인트는 한 문장으로 간결하게 (15-20자 내외)
        4. 핵심 수치나 통계 데이터 포함
        5. 마지막에 결론이나 핵심 메시지 추가
        
        요약 형식:
        # [제목]
        
        [간략한 소개 문장]
        
        • [핵심 포인트 1]
        • [핵심 포인트 2]
        ...
        
        [결론 메시지]
        """