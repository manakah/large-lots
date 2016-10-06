# -*- coding: utf-8 -*
import re
import json
from uuid import uuid4
from collections import OrderedDict
from datetime import datetime

import requests

import usaddress

from dateutil import parser

from django.shortcuts import render
from django.conf import settings
from django import forms
from django.utils import timezone
from django.template import Context
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect

from lots_admin.look_ups import DENIAL_REASONS, APPLICATION_STATUS
from lots_admin.models import Lot, Application, Address, ApplicationStep, ApplicationStatus

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
        pin = pin.replace("-", "")
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
    applications = Application.objects.all()
    return render(request, 'index.html', {
        'application_active': application_active(request),
        'applications': applications
        })

def application_active(request):
    apps = Application.objects.all()

    if settings.APPLICATION_DISPLAY: # override with configuration setting
        return True
    elif request.user.is_authenticated(): # or if you're logged in
        return True
    elif (settings.START_DATE < settings.CHICAGO_TIME < settings.END_DATE): # otherwise, check the dates
        return True
    else:
        return False

def get_ward(pin):
    carto = 'http://datamade.cartodb.com/api/v2/sql'
    params = {
        'api_key': settings.CARTODB_API_KEY,
        'q':  "SELECT ward FROM %s WHERE pin_nbr = '%s'" % \
            (settings.CURRENT_CARTODB, pin),
    }
    ward_nbr = None
    r = requests.get(carto, params=params)
    if r.status_code is 200:
        resp = json.loads(r.text)
        if resp['rows']:
            ward = resp['rows']
            ward_nbr = ward[0]['ward']
    return ward_nbr

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
    ward = get_ward(pin)
    add_info = {
        'street': address,
        'street_number': street_number,
        'street_dir': street_dir,
        'street_name': street_name,
        'street_type': street_type,
        'city': 'Chicago',
        'state': 'IL',
        'zip_code': '',
        'ward': ward
    }
    add_obj, created = Address.objects.get_or_create(**add_info)
    return add_obj

def apply(request):
    applications = Application.objects.all()

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        context = {}
        address_parts = ['street_number', 'street_dir', 'street_name', 'street_type']
        if form.is_valid():
            print(form.cleaned_data['lot_1_pin'])
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
                print(form.cleaned_data['lot_2_pin'])
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
            print(form.cleaned_data['owned_pin'])
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
                'tracking_id': str(uuid4()),
                'pilot': settings.CURRENT_PILOT
            }
            app = Application(**app_info)
            app.save()
            app.lot_set.add(lot1)
            if lot2:
                app.lot_set.add(lot2)
            app.save()

            # Create ApplicationStep and ApplicationStatus objects.
            app_step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['deed'], public_status='approved', step=2)

            app_status1 = ApplicationStatus(application=app, lot=lot1, current_step=app_step)
            app_status1.save()
            if lot2:
                app_status2 = ApplicationStatus(application=app, lot=lot2, current_step=app_step)
                app_status2.save()

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
            context['applications'] = applications
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
    return render(request, 'apply.html', {
        'form': form,
        'applications': applications
    })

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

def lot_uses(request):
    return render(request, 'lot-uses/index.html')

def lot_uses_page(request, use_id):

    use_id = int(use_id)
    if   use_id ==  1: return render(request, 'lot-uses/1-community-agriculture.html')
    elif use_id ==  2: return render(request, 'lot-uses/2-public-plazas-hardscaping.html')
    elif use_id ==  3: return render(request, 'lot-uses/3-landscapes-athletics.html')
    elif use_id ==  4: return render(request, 'lot-uses/4-dog-friendly-areas.html')
    elif use_id ==  5: return render(request, 'lot-uses/5-public-playgrounds.html')
    elif use_id ==  6: return render(request, 'lot-uses/6-sustainable-strategies.html')
    elif use_id ==  7: return render(request, 'lot-uses/7-furniture-objects-art.html')
    elif use_id ==  8: return render(request, 'lot-uses/8-shelters-sheds.html')
    elif use_id ==  9: return render(request, 'lot-uses/9-greenhouse.html')
    elif use_id == 10: return render(request, 'lot-uses/10-new-construction-building.html')
    elif use_id == 11: return render(request, 'lot-uses/11-building-addition.html')
    elif use_id == 12: return render(request, 'lot-uses/12-garage.html')
    elif use_id == 13: return render(request, 'lot-uses/13-pools-ponds-hot-tubs.html')
    elif use_id == 14: return render(request, 'lot-uses/14-porches-decks.html')
    elif use_id == 15: return render(request, 'lot-uses/15-driveways-patios.html')
    else: return HttpResponseRedirect('/lot-uses/')

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
            found_pins = list(set(re.findall('\d{2}-\d{2}-\d{3}-\d{3}-\d{4}', property_page.content.decode('utf-8'))))
            if found_pins:
                response['found_pins'] = found_pins
            else:
                response['found_pins'] = 'Not found'

    return HttpResponse(json.dumps(response), mimetype="application/json")

