from django.conf import settings
from django import forms

from .models import Application, Address


class AddressUpdateForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ('ward', 'community')

    def __init__(self, *args, **kwargs):
        super(AddressUpdateForm, self).__init__(*args, **kwargs)
        self.fields['zip_code'].required = False
