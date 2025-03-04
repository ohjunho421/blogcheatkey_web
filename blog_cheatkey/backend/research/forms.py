# research/forms.py
from django import forms

class ResearchFilterForm(forms.Form):
    keyword = forms.CharField(required=False, label='키워드')
    date_from = forms.DateField(required=False, label='시작일')
    date_to = forms.DateField(required=False, label='종료일')
    # 필요한 다른 필드 추가