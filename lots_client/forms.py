# -*- coding: utf-8 -*
import re
from io import BytesIO

import requests

import magic

from pdfid.pdfid import PDFiD

from django.conf import settings
from django import forms

from lots_admin.models import PrincipalProfile


class ApplicationForm(forms.Form):
    lot_1_address = forms.CharField(
        error_messages={'required': 'Provide the lot’s street address'},
        label="Lot 1 Street address")
    lot_1_pin = forms.CharField(
        error_messages={
            'required': 'Provide the lot’s Parcel Identification Number'
        },label="Lot 1 PIN")
    lot_1_use = forms.CharField(required=False)
    lot_2_address = forms.CharField(required=False)
    lot_2_pin = forms.CharField(required=False)
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
    organization = forms.CharField(required=False)
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

    def _check_pin(self, pin):
        carto = 'http://datamade.cartodb.com/api/v2/sql'
        pin = pin.replace('-', '')
        params = {
            'api_key': settings.CARTODB_API_KEY,
            'q': "SELECT pin_nbr FROM %s WHERE pin_nbr = '%s'" % (settings.CURRENT_CARTODB, pin),
        }
        r = requests.get(carto, params=params)
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
    social_security_number = forms.CharField()
    drivers_license_number = forms.CharField()
    license_plate_number = forms.CharField()
