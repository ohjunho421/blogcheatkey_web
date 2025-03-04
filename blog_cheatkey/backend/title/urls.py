# title/urls.py
from django.urls import path
from .views import (
    TitleGenerateView,
    TitleSelectView,
    SummaryCreateView
)

app_name = 'title'

urlpatterns = [
    path('<int:content_pk>/generate/', TitleGenerateView.as_view(), name='generate'),
    path('<int:pk>/select/', TitleSelectView.as_view(), name='select'),
    path('<int:content_pk>/summary/<str:summary_type>/', SummaryCreateView.as_view(), name='summary'),
]