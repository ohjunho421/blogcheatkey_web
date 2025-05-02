# history/urls.py
from django.urls import path
from .views import (
    HistoryListView,
    HistoryDetailView
)

app_name = 'history'

urlpatterns = [
    path('', HistoryListView.as_view(), name='list'),
    path('<int:pk>/', HistoryDetailView.as_view(), name='detail'),
]