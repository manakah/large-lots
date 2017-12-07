# -*- coding: utf-8 -*
import re
import json
import pytz
import os
from uuid import uuid4
from collections import OrderedDict
from datetime import datetime
from io import BytesIO

import requests

import usaddress

from dateutil import parser

import magic

from pdfid.pdfid import FindPDFHeaderRelaxed, C2BIP3, cBinaryFile

from django.shortcuts import render
from django.conf import settings
from django.utils import timezone
from django.template import Context
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
from django.forms import formset_factory

from lots_admin.look_ups import DENIAL_REASONS, APPLICATION_STATUS
from lots_admin.models import Lot, Application, Address, ApplicationStep,\
    ApplicationStatus, PrincipalProfile
from lots_client.forms import ApplicationForm, DeedUploadForm, PrincipalProfileForm


def home(request):
    applications = Application.objects.all()
    current_count = get_lot_count(settings.CURRENT_CARTODB)

    # Find all pins with active applications
    pins_under_review = set()
    for status in ApplicationStatus.objects.filter(denied=False).exclude(current_step__step=11):
        pins_under_review.add(status.lot_id)

    # Find all pins sold in the most recent LargeLots cycle
    pins_sold = set()
    for status in ApplicationStatus.objects.filter(denied=False).filter(current_step__step=11):
        pins_sold.add(status.lot_id)

    sold_count = get_lot_count('all_sold_lots') + len(pins_sold)
    
    return render(request, 'index.html', {
        'application_active': application_active(request),
        'applications': applications,
        'sold_count': sold_count,
        'current_count': current_count,
        'pins_under_review': pins_under_review,
        'pins_sold': pins_sold,
        })

def get_lot_count(cartoTable):
    carto = 'http://datamade.cartodb.com/api/v2/sql'
    params = {
        'api_key': settings.CARTODB_API_KEY,
        'q':  "SELECT count(*) FROM %s" % (cartoTable),
    }
    r = requests.get(carto, params=params)
    if r.status_code is 200:
        resp = json.loads(r.text)
        count = resp['rows']
        total = count[0]['count']
            
    return total

def application_active(request):
    apps = Application.objects.all()

    timezone = pytz.timezone('America/Chicago')
    chicago_time = datetime.now(timezone)

    if settings.APPLICATION_DISPLAY: # override with configuration setting
        return True
    elif request.user.is_authenticated(): # or if you're logged in
        return True
    elif (settings.START_DATE < chicago_time < settings.END_DATE): # otherwise, check the dates
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

def get_community(pin):
    carto = 'http://datamade.cartodb.com/api/v2/sql'
    params = {
        'api_key': settings.CARTODB_API_KEY,
        'q':  "SELECT community FROM %s WHERE pin_nbr = '%s'" % \
            (settings.CURRENT_CARTODB, pin),
    }
    community_name = None
    r = requests.get(carto, params=params)
    if r.status_code is 200:
        resp = json.loads(r.text)
        if resp['rows']:
            community = resp['rows']
            community_name = community[0]['community']

    return community_name

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
    community = get_community(pin)
    add_info = {
        'street': address,
        'street_number': street_number,
        'street_dir': street_dir,
        'street_name': street_name,
        'street_type': street_type,
        'city': 'Chicago',
        'state': 'IL',
        'zip_code': '',
        'ward': ward,
        'community': community,
    }
    add_obj, created = Address.objects.get_or_create(**add_info)
    return add_obj

def apply(request):
    applications = Application.objects.all()

    allLots = Lot.objects.all()

    applied_pins = [lot.pin for lot in allLots ]

    pins_str = ",".join(["'%s'" % a.replace('-','').replace(' ','') for a in applied_pins])

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
            return render(request, 'apply.html', context, {
                'applied_pins': pins_str
                })
    else:
        if application_active(request):
            form = ApplicationForm()
        else:
            form = None
    return render(request, 'apply.html', {
        'form': form,
        'applications': applications,
        'applied_pins': pins_str
    })

def apply_confirm(request, tracking_id):
    app = Application.objects.get(tracking_id=tracking_id)
    lots = [l for l in app.lot_set.all()]
    return render(request, 'apply_confirm.html', {'app': app, 'lots': lots})

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

def deed_upload(request, tracking_id):
    form          = DeedUploadForm()
    application   = Application.objects.get(tracking_id=tracking_id)
    lots          = [l for l in application.lot_set.all()]
    deed_uploaded = False

    if application.deed_image:
        deed_uploaded = True

    if request.method == 'POST':
        form = DeedUploadForm(request.POST, request.FILES)

        if form.is_valid():
            application = Application.objects.get(tracking_id=tracking_id)
            lots = [l for l in application.lot_set.all()]

            # Add deed.
            new_deed_image = form.cleaned_data['deed_image']
            application.deed_image = new_deed_image

            # Add timestamp.
            timezone = pytz.timezone('America/Chicago')
            application.deed_timestamp = datetime.now(timezone)
            application.save()

            # Send email.
            html_template = get_template('deed_upload_email.html')
            text_template = get_template('deed_upload_email.txt')
            context = Context({'app': application, 'lots': lots, 'host': request.get_host()})
            html_content = html_template.render(context)
            text_content = text_template.render(context)
            subject = 'Large Lots Deed Upload for %s %s' % (application.first_name, application.last_name)

            from_email = settings.EMAIL_HOST_USER
            to_email = [from_email]

            if application.email:
                to_email.append(application.email)

            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_content, 'text/html')
            msg.send()

            return HttpResponseRedirect('/upload-confirm/%s/' % tracking_id)

    return render(request, 'deed_upload.html', {
        'form': form,
        'tracking_id': tracking_id,
        'application': application,
        'lots': lots,
        'deed_uploaded': deed_uploaded,
    })

def upload_confirm(request, tracking_id):
    application = Application.objects.get(tracking_id=tracking_id)
    lots = [l for l in application.lot_set.all()]

    return render(request, 'upload_confirm.html', {
        'application': application,
        'lots': lots,
    })

def principal_profile_form(request):

    application = Application.objects.first()

    PrincipalProfileFormSet = formset_factory(PrincipalProfileForm, extra=0)

    # Prepopulate applicant's name and address
    initial_data = {
        'first_name': application.first_name,
        'last_name': application.last_name,
        'home_address': application.contact_address.street,
    }

    formset = PrincipalProfileFormSet(initial=[initial_data])

    if request.method == 'POST':
        formset = PrincipalProfileFormSet(request.POST)
        print(formset.data)
        if formset.is_valid():
            pass
#            profile = PrincipalProfile(**data)
#            profile.application = application
#            profile.save()

    return render(request, 'principal_profile.html', {
        'formset': formset,
        'application': application,
        'lots': application.lot_set.all(),
    })

def wintrust_invitation(request):
    with open('lots/static/images/Invitation_LargeLot_Workshop.pdf', 'rb') as pdf:
        response = HttpResponse(pdf.read(),content_type='application/pdf')
        response['Content-Disposition'] = 'filename=some_file.pdf'
        return response

def wintrust_announcement(request):
    with open('lots/static/images/Everyday_Loan_LargeLot.pdf', 'rb') as pdf:
        response = HttpResponse(pdf.read(),content_type='application/pdf')
        response['Content-Disposition'] = 'filename=some_file.pdf'
        return response

@csrf_exempt
def eds_submission(request):
    if request.method == 'POST':
        tracking_id = request.POST.get('tracking_id', None)
        if tracking_id:
            tracking_id = request.POST['tracking_id']
            try: 
                application = Application.objects.get(tracking_id=tracking_id)
                related_application_statuses = ApplicationStatus.objects.filter(application__email=application.email).filter(application__eds_sent=True).filter(current_step__step=7)

                for application_status in related_application_statuses:
                    step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['EDS_submission'], public_status='valid', step=8)
                    application_status.current_step = step
                    application_status.save()
                return HttpResponse('Successful EDS submission for {}'.format(application.email), status=200)

            except ObjectDoesNotExist: 
                return HttpResponse('Application does not exist', status=400)
        else:
            return HttpResponse('Did not find tracking_id in request: {}'.format(request), status=400)
    else:
        return HttpResponse('No EDS submission - not a post request: {}'.format(request.method), status=400)

