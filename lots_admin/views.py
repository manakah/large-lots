from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from operator import __or__ as OR
from functools import reduce
from lots_admin.models import Application, Lot, ApplicationStatus, ReviewStatus, DenialReason
from datetime import datetime
import csv
import json
from django import forms

def lots_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                login(request, user)
                return HttpResponseRedirect(reverse('lots_admin'))
    else:
        form = AuthenticationForm()
    return render(request, 'lots_login.html', {'form': form})

def lots_logout(request):
    logout(request)
    return HttpResponseRedirect('/')

@login_required(login_url='/lots-login/')
def lots_admin_map(request):
    applied_pins = set()
    for lot in Lot.objects.all():
        applied_pins.add(lot.pin)

    pins_str = ",".join(["'%s'" % a.replace('-','').replace(' ','') for a in applied_pins])
    return render(request, 'admin-map.html', {'applied_pins': pins_str})

@login_required(login_url='/lots-login/')
def lots_admin(request):
    applications = Application.objects.filter(pilot=settings.CURRENT_PILOT)
    return render(request, 'admin.html', {
        'applications': applications,
        'selected_pilot': settings.CURRENT_PILOT,
        'pilot_info': settings.PILOT_INFO})

@login_required(login_url='/lots-login/')
def pilot_admin(request, pilot):
    applications = Application.objects.filter(pilot=pilot)
    return render(request, 'admin.html', {
        'applications': applications,
        'selected_pilot': pilot,
        'pilot_info': settings.PILOT_INFO})

@login_required(login_url='/lots-login/')
def csv_dump(request, pilot):
    response = HttpResponse(content_type='text/csv')
    now = datetime.now().isoformat()
    response['Content-Disposition'] = 'attachment; filename=Large_Lots_Applications_%s_%s.csv' % (pilot, now)
    applications = Application.objects.filter(pilot=pilot)
    header = [
        'ID',
        'Date received',
        'First Name',
        'Last Name',
        'Organization',
        'Owned Address',
        'Owned Full Address',
        'Owned PIN',
        'Deed Image URL',
        'Contact Address',
        'Phone',
        'Email',
        'Received assistance',
        'Lot PIN',
        'Lot Address',
        'Lot Full Address',
        'Lot Image URL',
        'Lot Planned Use',
    ]
    rows = []
    for application in applications:
        owned_address = '%s %s %s %s' % \
            (getattr(application.owned_address, 'street', ''),
            getattr(application.owned_address, 'city', ''),
            getattr(application.owned_address, 'state', ''),
            getattr(application.owned_address, 'zip_code', ''))
        contact_address = '%s %s %s %s' % \
            (getattr(application.contact_address, 'street', ''),
            getattr(application.contact_address, 'city', ''),
            getattr(application.contact_address, 'state', ''),
            getattr(application.contact_address, 'zip_code', ''))
        for lot in application.lot_set.all():
            addr = getattr(lot.address, 'street', '').upper()
            addr_full = '%s %s %s %s' % \
                (getattr(lot.address, 'street', ''),
                getattr(lot.address, 'city', ''),
                getattr(lot.address, 'state', ''),
                getattr(lot.address, 'zip_code', ''))
            pin = lot.pin
            image_url = 'https://pic.datamade.us/%s.jpg' % pin.replace('-', '')
            lot_use = lot.planned_use


            rows.append([
                application.id,
                application.received_date.strftime('%Y-%m-%d %H:%m %p'),
                application.first_name,
                application.last_name,
                application.organization,
                getattr(application.owned_address, 'street', '').upper(),
                owned_address,
                application.owned_pin,
                application.deed_image.url,
                contact_address,
                application.phone,
                application.email,
                application.how_heard,
                pin,
                addr,
                addr_full,
                image_url,
                lot_use,
            ])
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response

@login_required(login_url='/lots-login/')
def deed_check(request, application_id):
    application = Application.objects.get(id=application_id)
    return render(request, 'deed_check.html', {
        'application': application
        })

@login_required(login_url='/lots-login/')
def pdfviewer(request):
    return render(request, 'pdfviewer.html')

@login_required(login_url='/lots-login/')
def deed_check_submit(request, application_id):
    if request.method == 'POST':
        application = Application.objects.get(id=application_id)
        user = request.user
        name = request.POST.get('name', 'off')
        address = request.POST.get('address', 'off')
        church = request.POST.get('church')
        # Move to step 3 of review process.
        if (name == 'on' and address == 'on' and church == '2'):
            application_status, created = ApplicationStatus.objects.get_or_create(description='Location and zoning check', public_status='approved', step=3)
            application.status = application_status
            rev_status, created = ReviewStatus.objects.get_or_create(reviewer=user, denied=False, email_sent=False)
            application.review_status = rev_status
            application.save()

            return HttpResponseRedirect('/application-review/step-3/%s/' % application.id)
        # Deny application.
        else:
            if (church == '1'):
                reason, created = DenialReason.objects.get_or_create(value="Applicant's owned property is a church", step=2)
            elif (name == 'off' and address == 'on'):
                reason, created = DenialReason.objects.get_or_create(value='Applicant name does not match deed', step=2)
            elif (name == 'on' and address == 'off'):
                reason, created = DenialReason.objects.get_or_create(value='Applicant address does not match deed', step=2)
            else:
                reason, created = DenialReason.objects.get_or_create(value='Applicant name and address do not match deed', step=2)
            rev_status, created = ReviewStatus.objects.get_or_create(reviewer=user, denied=True, email_sent=True, denial_reason=reason)
            application.review_status = rev_status
            application.save()

            return HttpResponseRedirect('/deny-application/%s/' % application.id)

@login_required(login_url='/lots-login/')
def location_check(request, application_id):
    application = Application.objects.get(id=application_id)

    # The following three lines reset ReviewStatus, in the event that the reviewer clicks "No, go back."
    rev_status, created = ReviewStatus.objects.get_or_create(reviewer=request.user, denied=False, email_sent=False)
    application.review_status = rev_status
    application.save()

    # Location of the applicant's property.
    owned_pin = application.owned_pin

    # Location(s) of properties the applicant applied for.
    applied_pins = [l.pin for l in application.lot_set.all()]

    # Find if other people have applied to the applicants' lots
    q_list = [Q(review_status__denied=False) | Q(review_status=None) | Q(status__step=4)]
    applicants_list = Application.objects.filter(lot__pin__in=applied_pins).filter(reduce(OR, q_list))

    # Location(s) of properties of other applicants who applied for the same property.
    other_owned_pins = [app.owned_pin for app in applicants_list ]
    other_owned_pins.remove(owned_pin)

    return render(request, 'location_check.html', {
        'application': application,
        'owned_pin': owned_pin,
        'applied_pins': applied_pins,
        'applicants_list': applicants_list,
        'other_owned_pins': other_owned_pins
        })

@login_required(login_url='/lots-login/')
def deny_application(request, application_id):
    application = Application.objects.get(id=application_id)
    return render(request, 'deny_application.html', {
        'application': application
        })

@login_required(login_url='/lots-login/')
def deny_submit(request, application_id):
    application = Application.objects.get(id=application_id)
    application.status = None
    application.save()
    return HttpResponseRedirect(reverse('lots_admin'))

@login_required(login_url='/lots-login/')
def location_check_submit(request, application_id):
    if request.method == 'POST':
        application = Application.objects.get(id=application_id)
        user = request.user
        block = request.POST.get('block', 'off')
        adjacent = request.POST.get('adjacent')

        if (block == 'on'):
            if (adjacent == '2'):
                # Deny application, since another applicant is adjacent to the property.
                reason, created = DenialReason.objects.get_or_create(value='Another applicant is adjacent to lot', step=3)
                rev_status, created = ReviewStatus.objects.get_or_create(reviewer=user, denied=True, email_sent=True, denial_reason=reason)
                application.review_status = rev_status
                application.save()
                return HttpResponseRedirect('/deny-application/%s/' % application.id)
            if (adjacent == '3'):
                # Application goes to a lottery.
                application_status, created = ApplicationStatus.objects.get_or_create(description='Multiple applicant check', public_status='approved', step=4)
                application.status = application_status
                rev_status, created = ReviewStatus.objects.get_or_create(reviewer=user, denied=False, email_sent=False)
                application.review_status = rev_status
                application.save()
                return HttpResponseRedirect(reverse('lots_admin'))

            # Move application to Step 5.
            application_status, created = ApplicationStatus.objects.get_or_create(description='Alderman letter of support', public_status='approved', step=5)
            application.status = application_status
            rev_status, created = ReviewStatus.objects.get_or_create(reviewer=user, denied=False, email_sent=False)
            application.review_status = rev_status
            application.save()

            # Deny other applicants.
            # Location(s) of properties the applicant applied for.
            applied_pins = [l.pin for l in application.lot_set.all()]
            q_list = [Q(review_status__denied=False) | Q(review_status=None) | Q(status__step=4)]
            #  Get list of other applicants.
            applicants = Application.objects.filter(lot__pin__in=applied_pins).filter(reduce(OR, q_list))
            applicants_list = list(applicants)
            applicants_list.remove(application)

            for a in applicants_list:
                print(a)
                reason, created = DenialReason.objects.get_or_create(value='Another applicant is adjacent to lot', step=3)
                rev_status, created = ReviewStatus.objects.get_or_create(reviewer=user, denied=True, email_sent=True, denial_reason=reason)
                a.review_status = rev_status
                a.status = None
                a.save()

            return HttpResponseRedirect(reverse('lots_admin'))
        else:
            # Deny application, since applicant does not live on same block as lot.
            reason, created = DenialReason.objects.get_or_create(value='Applicant is not on same block as lot', step=3)
            rev_status, created = ReviewStatus.objects.get_or_create(reviewer=user, denied=True, email_sent=True, denial_reason=reason)
            application.review_status = rev_status
            application.save()
            return HttpResponseRedirect('/deny-application/%s/' % application.id)

