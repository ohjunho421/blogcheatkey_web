# core/services/image_generator.py
import os
import re
import logging
import requests
import base64
from io import BytesIO
from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile
from openai import OpenAI
from content.models import BlogContent
from core.models import GeneratedImage
from key_word.models import Subtopic

logger = logging.getLogger(__name__)

class ImageGenerator:
    """
    블로그 콘텐츠 관련 이미지 생성 서비스
    """
    
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.openai_api_key)
        self.model = "dall-e-3"
        self.size = "1024x1024"
        self.quality = "standard"
    
    def generate_images_for_content(self, content_id):
        """
        블로그 콘텐츠의 각 소제목별 이미지 생성
        
        Args:
            content_id (int): BlogContent 모델의 ID
            
        Returns:
            list: 생성된 이미지 정보 목록
        """
        try:
            # 블로그 콘텐츠 정보 가져오기
            blog_content = BlogContent.objects.get(id=content_id)
            keyword = blog_content.keyword.keyword
            content = blog_content.content
            
            # 소제목 추출
            subtopics = self._extract_subtopics(content)
            
            # 이미 생성된 이미지 삭제 (새로 생성)
            GeneratedImage.objects.filter(blog_content=blog_content).delete()
            
            generated_images = []
            
            # 각 소제목별 이미지 생성
            for subtopic in subtopics:
                # 소제목 관련 내용 추출
                subtopic_content = self._extract_subtopic_content(content, subtopic)
                
                # 이미지 생성 프롬프트 생성
                prompt = self._create_image_prompt(keyword, subtopic, subtopic_content)
                
                # 이미지 생성
                image_url, alt_text = self._generate_image(prompt)
                
                if image_url:
                    # 이미지 다운로드 및 저장
                    image = self._save_image(blog_content, subtopic, image_url, prompt, alt_text)
                    if image:
                        generated_images.append({
                            'id': image.id,
                            'url': image.image.url,
                            'subtopic': subtopic,
                            'alt_text': image.alt_text
                        })
            
            return generated_images
            
        except BlogContent.DoesNotExist:
            logger.error(f"블로그 콘텐츠 ID {content_id}를 찾을 수 없습니다.")
            return []
        except Exception as e:
            logger.error(f"이미지 생성 중 오류: {str(e)}")
            return []
    
    def generate_infographic(self, content_id, subtopic_index=0):
        """
        블로그 콘텐츠의 특정 소제목에 대한 인포그래픽 생성
        
        Args:
            content_id (int): BlogContent 모델의 ID
            subtopic_index (int): 소제목 인덱스 (0부터 시작)
            
        Returns:
            dict: 생성된 인포그래픽 정보
        """
        try:
            # 블로그 콘텐츠 정보 가져오기
            blog_content = BlogContent.objects.get(id=content_id)
            keyword = blog_content.keyword.keyword
            content = blog_content.content
            
            # 소제목 추출
            subtopics = self._extract_subtopics(content)
            
            if not subtopics or subtopic_index >= len(subtopics):
                logger.error(f"소제목 인덱스 {subtopic_index}가 유효하지 않습니다.")
                return None
            
            subtopic = subtopics[subtopic_index]
            
            # 소제목 관련 내용 추출
            subtopic_content = self._extract_subtopic_content(content, subtopic)
            
            # 인포그래픽 생성 프롬프트 생성
            prompt = self._create_infographic_prompt(keyword, subtopic, subtopic_content)
            
            # 인포그래픽 생성
            image_url, alt_text = self._generate_image(prompt)
            
            if image_url:
                # 이미지 다운로드 및 저장
                image = self._save_image(blog_content, subtopic, image_url, prompt, alt_text, is_infographic=True)
                if image:
                    return {
                        'id': image.id,
                        'url': image.image.url,
                        'subtopic': subtopic,
                        'alt_text': image.alt_text
                    }
            
            return None
            
        except BlogContent.DoesNotExist:
            logger.error(f"블로그 콘텐츠 ID {content_id}를 찾을 수 없습니다.")
            return None
        except Exception as e:
            logger.error(f"인포그래픽 생성 중 오류: {str(e)}")
            return None
    
    def _extract_subtopics(self, content):
        """
        콘텐츠에서 소제목 추출
        
        Args:
            content (str): 블로그 콘텐츠
            
        Returns:
            list: 추출된 소제목 목록
        """
        subtopic_pattern = r'###\s+(.*?)\n'
        return re.findall(subtopic_pattern, content)
    
    def _extract_subtopic_content(self, content, subtopic):
        """
        콘텐츠에서 특정 소제목에 해당하는 내용 추출
        
        Args:
            content (str): 블로그 콘텐츠
            subtopic (str): 소제목
            
        Returns:
            str: 추출된 내용
        """
        # 소제목 위치 찾기
        subtopic_pattern = f'###\\s+{re.escape(subtopic)}\\s*\n'
        subtopic_matches = list(re.finditer(subtopic_pattern, content))
        
        if not subtopic_matches:
            return ""
        
        start_pos = subtopic_matches[0].end()
        
        # 다음 소제목 또는 참고자료 섹션 찾기
        next_section_pattern = r'(?:###\s+|##\s+참고자료)'
        next_section_matches = list(re.finditer(next_section_pattern, content[start_pos:]))
        
        if next_section_matches:
            end_pos = start_pos + next_section_matches[0].start()
        else:
            end_pos = len(content)
        
        # 추출된 내용 반환
        return content[start_pos:end_pos].strip()
    
    def _create_image_prompt(self, keyword, subtopic, content):
        """
        이미지 생성 프롬프트 생성
        
        Args:
            keyword (str): 키워드
            subtopic (str): 소제목
            content (str): 소제목 관련 내용
            
        Returns:
            str: 이미지 생성 프롬프트
        """
        # 통계 데이터 추출 (숫자, 퍼센트 등)
        stats_pattern = r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:%|퍼센트|명|개|원|달러|위|배|천|만|억)'
        statistics = re.findall(stats_pattern, content)
        
        # 핵심 키워드 추출
        key_terms = []
        for sentence in content.split('.'):
            words = sentence.strip().split()
            for word in words:
                if len(word) >= 2 and word not in ['그리고', '또한', '그러나', '하지만', '이것', '저것', '그것']:
                    key_terms.append(word)
        
        # 중복 제거 및 최대 5개 선택
        key_terms = list(set(key_terms))[:5]
        
        # 프롬프트 생성
        prompt = f"""
        Create a professional, blog-worthy image for a Korean blog post about '{keyword}' with subtitle '{subtopic}'.
        
        The image should be:
        - Clean, minimalist, and professional
        - Suitable for a business/informational blog
        - High quality, photorealistic
        - Clear and focused on the main subject
        - Well-lit with good contrast
        - No text overlay (will be added separately)
        
        Key concepts to include: {', '.join(key_terms) if key_terms else keyword}
        
        Content summary: {content[:200]}...
        
        Statistics (if relevant): {', '.join(statistics) if statistics else 'None'}
        
        Style: Clean, professional photography or high-quality 3D rendering, suitable for business blog.
        """
        
        return prompt
    
    def _create_infographic_prompt(self, keyword, subtopic, content):
        """
        인포그래픽 생성 프롬프트 생성
        
        Args:
            keyword (str): 키워드
            subtopic (str): 소제목
            content (str): 소제목 관련 내용
            
        Returns:
            str: 인포그래픽 생성 프롬프트
        """
        # 통계 데이터 추출 (숫자, 퍼센트 등)
        stats_pattern = r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:%|퍼센트|명|개|원|달러|위|배|천|만|억)'
        statistics = re.findall(stats_pattern, content)
        
        # 핵심 포인트 추출 (문장 단위)
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        key_points = sentences[:5]  # 최대 5개 문장 선택
        
        # 프롬프트 생성
        prompt = f"""
        Create a professional infographic for a Korean blog post about '{keyword}' with subtitle '{subtopic}'.
        
        The infographic should:
        - Have a clean, modern design with a white background
        - Include 3-5 key points presented as a flowchart or process
        - Use icons, simple illustrations, and minimal text
        - Use a consistent, professional color scheme
        - Have clear visual hierarchy and organization
        - Be easy to read and understand at a glance
        
        Key statistics to include: {', '.join(statistics) if statistics else 'None'}
        
        Main points to visualize:
        {chr(10).join([f"- {point}" for point in key_points]) if key_points else f"- Information about {keyword} related to {subtopic}"}
        
        Style: Clean, minimal infographic suitable for business/educational content. Think Harvard Business Review or McKinsey style visualizations.
        """
        
        return prompt
    
    def _generate_image(self, prompt):
        """
        OpenAI API를 사용하여 이미지 생성
        
        Args:
            prompt (str): 이미지 생성 프롬프트
            
        Returns:
            tuple: (이미지 URL, 대체 텍스트)
        """
        try:
            response = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=self.size,
                quality=self.quality,
                n=1
            )
            
            image_url = response.data[0].url
            alt_text = response.data[0].revised_prompt if hasattr(response.data[0], 'revised_prompt') else ""
            
            return image_url, alt_text
            
        except Exception as e:
            logger.error(f"이미지 생성 API 오류: {str(e)}")
            return None, None
    
    def _save_image(self, blog_content, subtopic, image_url, prompt, alt_text, is_infographic=False):
        """
        이미지 다운로드 및 저장
        
        Args:
            blog_content (BlogContent): 블로그 콘텐츠 객체
            subtopic (str): 소제목
            image_url (str): 이미지 URL
            prompt (str): 이미지 생성 프롬프트
            alt_text (str): 대체 텍스트
            is_infographic (bool): 인포그래픽 여부
            
        Returns:
            GeneratedImage: 저장된 이미지 객체
        """
        try:
            # 이미지 다운로드
            response = requests.get(image_url, timeout=10)
            if response.status_code != 200:
                logger.error(f"이미지 다운로드 실패: {response.status_code}")
                return None
            
            # 이미지 파일 생성
            image_content = ContentFile(response.content)
            
            # 파일명 생성
            keyword_slug = blog_content.keyword.keyword.replace(' ', '_').lower()
            subtopic_slug = subtopic.replace(' ', '_').lower()
            image_type = 'infographic' if is_infographic else 'image'
            file_name = f"{keyword_slug}_{subtopic_slug}_{image_type}.png"
            
            # 이미지 객체 생성 및 저장
            image = GeneratedImage(
                blog_content=blog_content,
                subtopic=subtopic,
                prompt=prompt,
                alt_text=alt_text[:200]  # 최대 200자로 제한
            )
            image.image.save(file_name, image_content, save=False)
            image.save()
            
            return image
            
        except Exception as e:
            logger.error(f"이미지 저장 중 오류: {str(e)}")
            return None