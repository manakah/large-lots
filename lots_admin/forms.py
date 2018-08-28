from django.conf import settings
from django import forms

from lots_client.utils import parse_address
from .models import Application, Address

class AddressUpdateForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ('street', )
        widgets = {
            'street': forms.TextInput(attrs={'class': 'form-control'}),
        }


    def __init__(self, *args, **kwargs):
        super(AddressUpdateForm, self).__init__(*args, **kwargs)
        self.can_delete = False

    def save(self, *args, **kwargs):
        street = self.cleaned_data['street']

        (street_number, street_dir, street_name, street_type, unit_number) = parse_address(street)

        add_info = {
            'street': street,
            'street_number': street_number,
            'street_dir': street_dir,
            'street_name': street_name,
            'street_type': street_type,
        }

        address = super(AddressUpdateForm, self).save(*args, **kwargs)
        for key, value in add_info.items():
            setattr(address, key, value)
        address.save()

        return address
        

