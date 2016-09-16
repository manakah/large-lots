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
from .look_ups import DENIAL_REASONS, APPLICATION_STATUS
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
def pdfviewer(request):
    return render(request, 'pdfviewer.html')

@login_required(login_url='/lots-login/')
def deny_application(request, application_id):
    application = Application.objects.get(id=application_id)
    review = ReviewStatus.objects.filter(application=application).latest('id')
    return render(request, 'deny_application.html', {
        'application': application,
        'review': review
        })

@login_required(login_url='/lots-login/')
def deny_submit(request, application_id):
    application = Application.objects.get(id=application_id)
    application.status = None
    application.save()
    return HttpResponseRedirect(reverse('lots_admin'))

@login_required(login_url='/lots-login/')
def deed_check(request, application_id):
    application = Application.objects.get(id=application_id)
    # Delete last ReviewStatus, if someone hits "no, go back" on deny page.
    ReviewStatus.objects.filter(application=application, step_completed=2).delete()
    application.denied = False
    application.save()
    return render(request, 'deed_check.html', {
        'application': application
        })

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
            application_status, created = ApplicationStatus.objects.get_or_create(description=APPLICATION_STATUS['location'], public_status='approved', step=3)
            application.status = application_status
            rev_status = ReviewStatus(reviewer=user, email_sent=False, application=application, step_completed=2)
            rev_status.save()
            application.save()

            return HttpResponseRedirect('/application-review/step-3/%s/' % application.id)
        # Deny application.
        else:
            if (church == '1'):
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['church'])
            elif (name == 'off' and address == 'on'):
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['name'])
            elif (name == 'on' and address == 'off'):
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['address'])
            else:
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['name-address'])
            rev_status = ReviewStatus(reviewer=user, email_sent=True, denial_reason=reason, application=application, step_completed=2)
            rev_status.save()
            application.denied = True
            application.save()

            return HttpResponseRedirect('/deny-application/%s/' % application.id)

@login_required(login_url='/lots-login/')
def location_check(request, application_id):
    application = Application.objects.get(id=application_id)
    # Delete last ReviewStatus, if someone hits "no, go back" on deny page.
    ReviewStatus.objects.filter(application=application, step_completed=3).delete()
    application.denied = False
    application.save()
    # Location of the applicant's property.
    owned_pin = application.owned_pin
    # Location(s) of properties the applicant applied for.
    applied_pins = [l.pin for l in application.lot_set.all()]

    return render(request, 'location_check.html', {
        'application': application,
        'owned_pin': owned_pin,
        'applied_pins': applied_pins
        })

@login_required(login_url='/lots-login/')
def location_check_submit(request, application_id):
    if request.method == 'POST':
        application = Application.objects.get(id=application_id)
        user = request.user
        block = request.POST.get('block', 'off')

        if (block == 'on'):
            # Update ReviewStatus.
            rev_status = ReviewStatus(reviewer=user, email_sent=False, application=application, step_completed=3)
            rev_status.save()

            # Are there other applicants on this property?
            applied_pins = [l.pin for l in application.lot_set.all()]
            applicants = Application.objects.filter(lot__pin__in=applied_pins).filter(denied=False)
            applicants_list = list(applicants)

            if (len(applicants_list) > 1):
                # If there are other applicants: move application to Step 4.
                application_status, created = ApplicationStatus.objects.get_or_create(description=APPLICATION_STATUS['multi'], public_status='approved', step=4)
                application.status = application_status
                application.save()

                return HttpResponseRedirect('/application-review/step-4/%s/' % application.id)
            else:
                # No other applicants: move application to Step 5.
                application_status, created = ApplicationStatus.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='approved', step=6)
                application.status = application_status
                application.save()

                return HttpResponseRedirect(reverse('lots_admin'))
        else:
            # Deny application, since applicant does not live on same block as lot.
            reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['block'])
            rev_status = ReviewStatus(reviewer=user, email_sent=True, denial_reason=reason, application=application, step_completed=3)
            rev_status.save()
            application.denied = True
            application.save()

            return HttpResponseRedirect('/deny-application/%s/' % application.id)

@login_required(login_url='/lots-login/')
def multiple_applicant_check(request, application_id):
    application = Application.objects.get(id=application_id)

     # Delete last ReviewStatus, if someone hits "no, go back" on deny page.
    ReviewStatus.objects.filter(application=application, step_completed=4).delete()
    application.denied = False
    application.save()

    # Location of the applicant's property.
    owned_pin = application.owned_pin

    # Location(s) of properties the applicant applied for.
    applied_pins = [l.pin for l in application.lot_set.all()]

    # Are there other applicants on this property?
    applied_pins = [l.pin for l in application.lot_set.all()]
    applicants = Application.objects.filter(lot__pin__in=applied_pins).filter(denied=False)
    applicants_list = list(applicants)

    # Location(s) of properties of other applicants who applied for the same property.
    other_owned_pins = [app.owned_pin for app in applicants_list ]
    other_owned_pins.remove(owned_pin)

    return render(request, 'multiple_applicant_check.html', {
        'application': application,
        'owned_pin': owned_pin,
        'applied_pins': applied_pins,
        'applicants_list': applicants_list,
        'other_owned_pins': other_owned_pins
        })

@login_required(login_url='/lots-login/')
def multiple_location_check_submit(request, application_id):
    if request.method == 'POST':
        application = Application.objects.get(id=application_id)
        user = request.user
        adjacent = request.POST.get('adjacent')

        if (adjacent == '2'):
            # Deny application, since another applicant is adjacent to the property.
            reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['adjacent'])
            rev_status = ReviewStatus(reviewer=user, email_sent=True, denial_reason=reason, application=application, step_completed=4)
            rev_status.save()
            application.denied = True
            application.save()

            return HttpResponseRedirect('/deny-application/%s/' % application.id)

        elif (adjacent == '3'):
            # Application goes to Step 5: lottery.
            application_status, created = ApplicationStatus.objects.get_or_create(description=APPLICATION_STATUS['lottery'], public_status='approved', step=5)
            application.status = application_status
            application.save()
            rev_status = ReviewStatus(reviewer=user, email_sent=False, application=application, step_completed=4)
            rev_status.save()

            return HttpResponseRedirect(reverse('lots_admin'))
        else:
            # Move application to Step 6.
            application_status, created = ApplicationStatus.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='approved', step=6)
            application.status = application_status
            application.save()
            rev_status = ReviewStatus(reviewer=user, email_sent=False, application=application, step_completed=4)
            rev_status.save()

            # Deny other applicants.
            # Location(s) of properties the applicant applied for.
            applied_pins = [l.pin for l in application.lot_set.all()]
            applicants = Application.objects.filter(lot__pin__in=applied_pins).filter(denied=False)
            applicants_list = list(applicants)
            applicants_list.remove(application)

            for a in applicants_list:
                ReviewStatus.objects.filter(application=a, step_completed=4).delete()
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['adjacent'])
                rev_status = ReviewStatus(reviewer=user, email_sent=True, denial_reason=reason, application=a, step_completed=4)
                rev_status.save()
                a.denied = True
                a.status = None
                a.save()

            return HttpResponseRedirect(reverse('lots_admin'))

@login_required(login_url='/lots-login/')
def review_status_log(request, application_id):
    application = Application.objects.get(id=application_id)
    reviews = ReviewStatus.objects.filter(application=application)
    return render(request, 'review_status_log.html', {
        'application': application,
        'reviews': reviews
        })