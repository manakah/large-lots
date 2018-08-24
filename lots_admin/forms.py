from django.conf import settings
from django import forms

from .models import Application

class ApplicationUpdateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ('owned_pin', 'owned_address')
