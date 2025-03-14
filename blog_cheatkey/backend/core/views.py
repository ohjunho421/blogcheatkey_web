# core/views.py
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .services.image_generator import ImageGenerator
from .models import GeneratedImage

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def generate_images_for_content(request, content_id):
    """모든 소제목에 대한 이미지 생성"""
    image_generator = ImageGenerator()
    generated_images = image_generator.generate_images_for_content(content_id)
    return JsonResponse(generated_images, safe=False)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_infographic(request, content_id):
    """특정 소제목에 대한 인포그래픽 생성"""
    subtopic_index = request.data.get('subtopic_index', 0)
    image_generator = ImageGenerator()
    infographic = image_generator.generate_infographic(content_id, subtopic_index)
    if infographic:
        return JsonResponse(infographic)
    return JsonResponse({'error': '인포그래픽 생성 실패'}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_generated_images(request, content_id):
    """블로그 콘텐츠에 대한 생성된 이미지 목록 조회"""
    images = GeneratedImage.objects.filter(blog_content_id=content_id)
    images_data = [
        {
            'id': image.id,
            'url': image.image.url,
            'subtopic': image.subtopic,
            'alt_text': image.alt_text,
            'is_infographic': 'infographic' in image.image.name
        }
        for image in images
    ]
    return JsonResponse(images_data, safe=False)