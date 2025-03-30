from rest_framework import generics, permissions
from .models import ContentHistory
from .serializers import ContentHistorySerializer

class HistoryListView(generics.ListAPIView):
    """
    사용자의 콘텐츠 히스토리 목록을 반환하는 뷰
    """
    serializer_class = ContentHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ContentHistory.objects.filter(user=self.request.user)

class HistoryDetailView(generics.RetrieveAPIView):
    """
    특정 콘텐츠 히스토리의 상세 정보를 반환하는 뷰
    """
    serializer_class = ContentHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ContentHistory.objects.filter(user=self.request.user)