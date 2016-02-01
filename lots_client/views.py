# -*- coding: utf-8 -*

import re
from django.shortcuts import render
from django.conf import settings
from django import forms
from django.utils import timezone
from django.template import Context
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
from lots_admin.models import Lot, Application, Address
import requests
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect
import json
from uuid import uuid4
from collections import OrderedDict
from datetime import datetime
from dateutil import parser
import usaddress

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
    email = forms.CharField(required=False)
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
        params = {
            'api_key': settings.CARTODB_API_KEY,
            'q': "SELECT pin14 FROM %s WHERE pin14 = '%s' AND city_owned='T' AND residential='T' AND alderman_hold != 'T'" % (pin.replace('-', ''), settings.CURRENT_CARTODB),
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

    def clean_lot_1_pin(self):
        return self._clean_pin('lot_1_pin')

    def clean_lot_2_pin(self):
        if self.cleaned_data['lot_2_pin']:
            return self._clean_pin('lot_2_pin')
        return self.cleaned_data['lot_2_pin']
    
    def clean_owned_pin(self):
        pin = self.cleaned_data['owned_pin']
        pattern = re.compile('[^0-9]')
        if len(pattern.sub('', pin)) != 14:
            raise forms.ValidationError('Please provide a valid PIN')
        else:
            return pin

    def clean_deed_image(self):
        image = self.cleaned_data['deed_image']._get_name()
        ftype = image.split('.')[-1]
        if ftype.lower() not in ['pdf', 'png', 'jpg', 'jpeg', 'gif']:
            raise forms.ValidationError('File type not supported. Please choose an image or PDF.')
        return self.cleaned_data['deed_image']

def home(request):
    return render(request, 'index.html', {'application_active': application_active(request)})

def application_active(request):
    chicago_time = timezone.localtime(timezone.now())
    start_date = timezone.make_aware(datetime(2016, 2, 1, 0, 0),
        timezone.get_current_timezone())
    end_date = timezone.make_aware(datetime(2016, 3, 21, 23, 59),
        timezone.get_current_timezone())
    
    if settings.APPLICATION_DISPLAY: # override with configuration setting
        return True
    elif request.user.is_authenticated(): # or if you're logged in
        return True
    elif start_date < chicago_time < end_date: # otherwise, check the dates
        return True
    else:
        return False

def get_lon_lat(pin):
    carto = 'http://datamade.cartodb.com/api/v2/sql'
    params = {
        'api_key': settings.CARTODB_API_KEY,
        'q':  "SELECT longitude, latitude FROM %s WHERE pin14 = '%s'" % \
            (unicode(pin).replace('-', ''), settings.CURRENT_CARTODB),
    }
    r = requests.get(carto, params=params)
    longitude, latitude = None, None
    if r.status_code is 200:
        resp = r.json()['rows']
        if resp:
            longitude, latitude = resp[0]['longitude'], resp[0]['latitude']
    return longitude, latitude

def parse_address(address):
    parsed = usaddress.parse(address)

    street_number = ' '.join([p[0] for p in parsed if p[1] == 'AddressNumber'])
    street_dir = ' '.join([p[0] for p in parsed if p[1] == 'StreetNamePreDirectional'])
    street_name = ' '.join([p[0] for p in parsed if p[1] == 'StreetName'])
    street_type = ' '.join([p[0] for p in parsed if p[1] == 'StreetNamePostType'])
    unit_number = ' '.join([p[0] for p in parsed if p[1] == 'OccupancyIdentifier'])

    return (street_number, street_dir, street_name, street_type, unit_number)

def get_lot_address(address, pin):
    (street_number, street_dir, street_name, street_type, unit_number) = parse_address(address)
    longitude, latitude = get_lon_lat(pin)
    add_info = {
        'street': address,
        'street_number': street_number,
        'street_dir': street_dir,
        'street_name': street_name,
        'street_type': street_type,
        'longitude': longitude,
        'latitude': latitude,
        'city': 'Chicago',
        'state': 'IL',
        'zip_code': '',
    }
    add_obj, created = Address.objects.get_or_create(**add_info)
    return add_obj

def apply(request):
    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        context = {}
        address_parts = ['street_number', 'street_dir', 'street_name', 'street_type']
        if form.is_valid():
            l1_address = get_lot_address(form.cleaned_data['lot_1_address'], 
                                         form.cleaned_data['lot_1_pin'])
            lot1_info = {
                'pin': form.cleaned_data['lot_1_pin'],
                'address': l1_address,
                'planned_use': form.cleaned_data.get('lot_1_use')
            }
            try:
                lot1 = Lot.objects.get(pin=lot1_info['pin'])
            except Lot.DoesNotExist:
                lot1 = Lot(**lot1_info)
                lot1.save()
            lot2 = None
            if form.cleaned_data.get('lot_2_pin'):
                l2_address = get_lot_address(form.cleaned_data['lot_2_address'],
                                             form.cleaned_data['lot_2_pin'])
                lot2_info = {
                    'pin': form.cleaned_data['lot_2_pin'],
                    'address': l2_address,
                    'planned_use': form.cleaned_data.get('lot_2_use')
                }
                try:
                    lot2 = Lot.objects.get(pin=lot2_info['pin'])
                except Lot.DoesNotExist:
                    lot2 = Lot(**lot2_info)
                    lot2.save()
            c_address_info = {
                'street': form.cleaned_data['contact_street'],
                'city': form.cleaned_data['contact_city'],
                'state': form.cleaned_data['contact_state'],
                'zip_code': form.cleaned_data['contact_zip_code']
            }
            c_address, created = Address.objects.get_or_create(**c_address_info)
            owned_address = get_lot_address(form.cleaned_data['owned_address'],
                                            form.cleaned_data['owned_pin'])
            app_info = {
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'organization': form.cleaned_data.get('organization'),
                'owned_address': owned_address,
                'owned_pin': form.cleaned_data['owned_pin'],
                'deed_image': form.cleaned_data['deed_image'],
                'contact_address': c_address,
                'phone': form.cleaned_data['phone'],
                'email': form.cleaned_data.get('email'),
                'how_heard': form.cleaned_data.get('how_heard'),
                'tracking_id': unicode(uuid4()),
                'pilot': settings.CURRENT_PILOT,
            }
            app = Application(**app_info)
            app.save()
            app.lot_set.add(lot1)
            if lot2:
                app.lot_set.add(lot2)
            app.save()
            
            html_template = get_template('apply_html_email.html')
            text_template = get_template('apply_text_email.txt')
            lots = [l for l in app.lot_set.all()]
            context = Context({'app': app, 'lots': lots, 'host': request.get_host()})
            html_content = html_template.render(context)
            text_content = text_template.render(context)
            subject = 'Large Lots Application for %s %s' % (app.first_name, app.last_name)
            
            from_email = settings.EMAIL_HOST_USER
            to_email = [from_email]

            # if provided, send confirmation email to applicant
            if app.email:
                to_email.append(app.email)

            # send email confirmation to info@largelots.org
            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_content, 'text/html')
            msg.send()

            return HttpResponseRedirect('/apply-confirm/%s/' % app.tracking_id)
        else:
            context['lot_1_address'] = form['lot_1_address'].value()
            context['lot_1_pin'] = form['lot_1_pin'].value()
            context['lot_1_use'] = form['lot_1_use'].value()
            context['lot_2_address'] = form['lot_2_address'].value()
            context['lot_2_pin'] = form['lot_2_pin'].value()
            context['lot_2_use'] = form['lot_2_use'].value()
            context['owned_address'] = form['owned_address'].value()
            context['owned_pin'] = form['owned_pin'].value()
            context['deed_image'] = form['deed_image'].value()
            context['first_name'] = form['first_name'].value()
            context['last_name'] = form['last_name'].value()
            context['organization'] = form['organization'].value()
            context['phone'] = form['phone'].value()
            context['email'] = form['email'].value()
            context['contact_street'] = form['contact_street'].value()
            context['contact_city'] = form['contact_city'].value()
            context['contact_state'] = form['contact_state'].value()
            context['contact_zip_code'] = form['contact_zip_code'].value()
            context['how_heard'] = form['how_heard'].value()
            context['terms'] = form['terms'].value()
            context['form'] = form
            fields = [f for f in form.fields]
            context['error_messages'] = OrderedDict()
            for field in fields:
                label = form.fields[field].label
                error = form.errors.get(field)
                if label and error:
                    context['error_messages'][label] = form.errors[field][0]
            return render(request, 'apply.html', context)
    else:
        if application_active(request):
            form = ApplicationForm()
        else:
            form = None
    return render(request, 'apply.html', {'form': form})

def apply_confirm(request, tracking_id):
    app = Application.objects.get(tracking_id=tracking_id)
    lots = [l for l in app.lot_set.all()]
    return render(request, 'apply_confirm.html', {'app': app, 'lots': lots})

def status_pilot_1(request):
    return render(request, 'status_pilot_1.html')

def status_pilot_2(request):
    return render(request, 'status_pilot_2.html')

def status_pilot_3(request):
    return render(request, 'status_pilot_3.html')

def status_pilot_4(request):
    return render(request, 'status_pilot_4.html')

def faq(request):
    return render(request, 'faq.html')

def about(request):
    return render(request, 'about.html')

def get_pin_from_address(request):

    address = request.GET.get('address', '')
    response = {'status': 'ok', 'address': address, 'found_pins': 'Not found'}

    if address != '':
        (street_number, street_dir, street_name, street_type, unit_number) = parse_address(address)
        response['address_components'] = {
            'street_number': street_number, 
            'street_direction': street_dir, 
            'street_name': street_name,
            'unit_number': unit_number
        }

        response['source_url'] = 'http://cookcountypropertyinfo.com/Pages/Address-Results.aspx?hnum=%s&dir=%s&sname=%s&city=Chicago&zip=&unit=%s' % (street_number, street_dir, street_name, unit_number)

        # http://cookcountypropertyinfo.com/Pages/Address-Results.aspx?hnum=444&sname=Wabash&city=Chicago&zip=&unit=&dir=N
        property_page = requests.get(response['source_url'])
        if property_page.status_code is 200:
            found_pins = list(set(re.findall('\d{2}-\d{2}-\d{3}-\d{3}-\d{4}', property_page.content)))
            if found_pins:
                response['found_pins'] = found_pins
            else:
                response['found_pins'] = 'Not found'

    return HttpResponse(json.dumps(response), mimetype="application/json") 
