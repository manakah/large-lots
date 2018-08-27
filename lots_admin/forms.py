from django.conf import settings
from django import forms

from .models import Application, Address


class AddressUpdateForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ('ward', 'community')

class ApplicationUpdateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ('owned_pin', )

    def __init__(self, *args, **kwargs):
        super(ApplicationUpdateForm, self).__init__(*args, **kwargs)

        self.address_form = AddressUpdateForm(instance=self.instance and self.instance.owned_address)
