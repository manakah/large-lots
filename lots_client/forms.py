# -*- coding: utf-8 -*
import re
from io import BytesIO

import requests

import magic

from pdfid.pdfid import PDFiD

from django.conf import settings
from django import forms

from us.states import STATES

from lots_admin.models import PrincipalProfile


class ApplicationForm(forms.Form):
    lot_1_pin = forms.CharField(
        error_messages={
            'required': 'Provide the lot’s Parcel Identification Number'
        },label="Lot 1 PIN")
    lot_1_address = forms.CharField(
        error_messages={'required': 'Provide the lot’s street address'},
        label="Lot 1 Street address")
    lot_1_use = forms.CharField(required=False)
    lot_2_pin = forms.CharField(required=False)
    lot_2_address = forms.CharField(required=False)
    lot_2_use = forms.CharField(required=False)
    owned_address = forms.CharField(
        error_messages={
            'required': 'Provide the address of the building you own'
        }, label="Owned property address")
    owned_pin = forms.CharField(
        error_messages={
            'required': 'Provide the Parcel Identification Number for the property you own'
        },label="Owned PIN")
    deed_image = forms.FileField(
        error_messages={'required': 'Provide an image of the deed of the building you own'
        }, label="Electronic version of your deed")
    first_name = forms.CharField(
        error_messages={'required': 'Provide your first name'},
        label="Your first name")
    last_name = forms.CharField(
        error_messages={'required': 'Provide your last name'},
        label="Your last name")
    organization_confirmed = forms.BooleanField(required=False)
    organization = forms.CharField(required=False,
        label="Your organization")
    phone = forms.CharField(
        error_messages={'required': 'Provide a contact phone number'},
        label="Your phone number")
    email = forms.CharField(
        error_messages={'required': 'Provide an email address'},
        label="Your email address")
    contact_street = forms.CharField(
        error_messages={'required': 'Provide a complete address'},
        label="Your contact address")
    contact_city = forms.CharField()
    contact_state = forms.CharField()
    contact_zip_code = forms.CharField()
    how_heard = forms.CharField(required=False)
    terms = forms.BooleanField(
        error_messages={'required': 'Verify that you have read and agree to the terms'},
        label="Application terms")

    '''
    Possible combinations of user input for organization (text) and organization_confirmed (checkbox):
    (1) The user does not check the confirm box and does not input an org name - VALID 
    (2) The user checks the confirm box and inputs an org name - VALID 
    (3) The user checks the confirm box but does NOT input an org name - INVALID

    (4) The user checks the confirm box, enters an org name, and then unchecks the box: this validates as expected. The confirm box will be False, and the input will be None, since a "disabled" field always returns None.
    '''
    def clean_organization(self):
        organization = self.cleaned_data['organization']
        organization_confirmed = self.cleaned_data['organization_confirmed']

        if organization_confirmed and not organization:
            message = 'Check the box and enter an organization name, or leave both blank.'
            raise forms.ValidationError(message)

        return organization

    # Query Carto
    def call_carto(self, query_args, pin):
        carto = 'http://datamade.cartodb.com/api/v2/sql'
        pin = pin.replace('-', '')
        params = {
            'api_key': settings.CARTODB_API_KEY,
            'q': "SELECT {query_args} FROM {carto_table} WHERE pin_nbr='{pin_nbr}'" \
                .format(query_args=query_args,
                        carto_table=settings.CURRENT_CARTODB,
                        pin_nbr=pin),
        }

        r = requests.get(carto, params=params)

        return r

    # Properly format an address, given an object as input.
    def format_address(self, address_obj):
        low_address = address_obj['low_address']
        street_direction = address_obj['street_direction']
        street_name = address_obj['street_name']
        street_type = address_obj['street_type']

        return "{low_address} {street_direction} {street_name} {street_type}".format(low_address=low_address, 
                                                                                    street_direction=street_direction, 
                                                                                    street_name=street_name,
                                                                                    street_type=street_type)

    # Calls helper functions: acquires an address with matching the PIN from Carto, and formats the address. 
    def generate_address_from_pin(self, pin):
        r = self.call_carto("low_address, street_direction, street_name, street_type", pin)
        
        if r.status_code == 200:
            if r.json()['total_rows'] == 1:
                return self.format_address(r.json()['rows'][0])
            else:
                message = '%s is not available for purchase. \
                    Please select one from the map above' % pin
                raise forms.ValidationError(message)

    
    def clean_lot_1_address(self):
        pin = self.cleaned_data['lot_1_pin']
        address = self.generate_address_from_pin(pin)
        if address:
            return address

        return self.cleaned_data['lot_1_address']

    def _check_pin(self, pin):
        # carto = 'http://datamade.cartodb.com/api/v2/sql'
        # pin = pin.replace('-', '')
        # params = {
        #     'api_key': settings.CARTODB_API_KEY,
        #     'q': "SELECT pin_nbr FROM %s WHERE pin_nbr = '%s'" % (settings.CURRENT_CARTODB, pin),
        # }
        # r = requests.get(carto, params=params)

        r = self.call_carto("pin_nbr", pin)

        if r.status_code == 200:
            if r.json()['total_rows'] == 1:
                return pin
            else:
                message = '%s is not available for purchase. \
                    Please select one from the map above' % pin
                raise forms.ValidationError(message)
        else:
            return pin

    def _clean_pin(self, key):
        pin = self.cleaned_data[key]
        pattern = re.compile('[^0-9]')
        if len(pattern.sub('', pin)) != 14:
            raise forms.ValidationError('Please provide a valid PIN')
        else:
            return self._check_pin(pin)

    def _clean_phone(self, key):
        phone = self.cleaned_data[key]
        pattern = re.compile('[^0-9]')
        if len(pattern.sub('', phone)) != 10:
            raise forms.ValidationError('Please provide a valid phone (10 digits)')
        else:
            return phone

    def clean_phone(self):
        return self._clean_phone('phone')

    def clean_lot_1_pin(self):
        return self._clean_pin('lot_1_pin')

    def clean_lot_2_pin(self):
        if self.cleaned_data['lot_2_pin']:
            return self._clean_pin('lot_2_pin')
        return self.cleaned_data['lot_2_pin']

    def clean_owned_pin(self):
        pin = self.cleaned_data['owned_pin']
        pin = pin.replace("-", "").replace(" ", "")
        pattern = re.compile('[^0-9]')
        if len(pattern.sub('', pin)) != 14:
            raise forms.ValidationError('Please provide a valid PIN')
        else:
            return pin

    def clean_deed_image(self):

        image = self.cleaned_data['deed_image']
        filetype = magic.from_buffer(image.file.read(), mime=True)

        image.file.seek(0)

        ok_types = [
            'image/gif',
            'image/jpeg',
            'image/png',
            'application/pdf'
        ]

        if filetype == 'application/pdf':

            outfile = BytesIO()

            _, self.cleaned_data['deed_image'].file = PDFiD(image.file,
                                                            disarm=True,
                                                            outfile=outfile)

        elif filetype not in ok_types:
            raise forms.ValidationError('File type not supported. Please choose an image or PDF.')

        return self.cleaned_data['deed_image']

class DeedUploadForm(forms.Form):
    deed_image = forms.FileField(
        error_messages={'required': 'Provide an image of the deed of the building you own'
        }, label="Electronic version of your deed")

    def clean_deed_image(self):

        image = self.cleaned_data['deed_image']
        filetype = magic.from_buffer(image.file.read(), mime=True)

        image.file.seek(0)

        ok_types = [
            'image/gif',
            'image/jpeg',
            'image/png',
            'application/pdf'
        ]

        if filetype not in ok_types:
            raise forms.ValidationError('File type not supported. Please choose an image or PDF.')

        return self.cleaned_data['deed_image']


class PrincipalProfileForm(forms.Form):
    first_name = forms.CharField()
    last_name = forms.CharField()
    home_address = forms.CharField()
    date_of_birth = forms.DateField(widget=forms.SelectDateWidget(
        years=[year for year in range(2017, 1900, -1)],
        attrs={'class': 'form-control'})
    )
    social_security_number = forms.CharField(max_length=11)
    drivers_license_state = forms.ChoiceField(
        label="Driver's license state",
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    drivers_license_number = forms.CharField(
        label="Driver's license number",
        max_length=20,
        required=False
    )
    license_plate_state = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    license_plate_number = forms.CharField(
        max_length=10,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['drivers_license_state'].choices = self._state_choices
        self.fields['license_plate_state'].choices = self._state_choices

    @property
    def _state_choices(self):
        choices = [(None, 'State'), ['NA', 'NA']]
        choices += [(state.abbr, state.name) for state in STATES]
        return choices

    def _clean_number(self, field):
        number = self.cleaned_data[field]

        state_field = field.replace('number', 'state')
        state_data = self.cleaned_data.get(state_field)

        if state_data != 'NA' and not number:
            message = 'This field is required.'
            raise forms.ValidationError(message)

        return self.cleaned_data[field]

    def clean_license_plate_number(self):
        return self._clean_number('license_plate_number')

    def clean_drivers_license_number(self):
        return self._clean_number('drivers_license_number')

    def clean_social_security_number(self):
        ssn = self.cleaned_data['social_security_number']

        digits = [char for char in ssn if char.isdigit()]

        if not len(digits) == 9:
            message = "Please enter a 9-digit Social Security number."
            raise forms.ValidationError(message)

        return '%s-%s-%s' % (''.join(digits[:3]),
                             ''.join(digits[3:5]),
                             ''.join(digits[5:]))
