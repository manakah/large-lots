import csv
import json
from operator import __or__ as OR
from functools import reduce
from datetime import datetime
from django import forms

from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.template import Context
from django.template.loader import get_template
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q

from .look_ups import DENIAL_REASONS, APPLICATION_STATUS
from lots_admin.models import Application, Lot, ApplicationStep, Review, ApplicationStatus, DenialReason

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
    application_status_list = ApplicationStatus.objects.filter(application__pilot=settings.CURRENT_PILOT)
    before_step4 = ApplicationStatus.objects.filter(Q(current_step__step=2) | Q(current_step__step=3))
    on_step4 = ApplicationStatus.objects.filter(current_step__step=4)
    alderman_letter = ApplicationStatus.objects.filter(current_step__step=6)

    return render(request, 'admin.html', {
        'application_status_list': application_status_list,
        'selected_pilot': settings.CURRENT_PILOT,
        'pilot_info': settings.PILOT_INFO,
        'before_step4': before_step4,
        'on_step4': on_step4,
        'alderman_letter': alderman_letter
        })

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
    application_status = ApplicationStatus.objects.get(id=application_id)
    review = Review.objects.filter(application=application_status).latest('id')
    return render(request, 'deny_application.html', {
        'application_status': application_status,
        'review': review
        })

@login_required(login_url='/lots-login/')
def deny_submit(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    application_status.current_step = None
    application_status.save()

    send_email(request, application_status, "deny")

    return HttpResponseRedirect(reverse('lots_admin'))


@login_required(login_url='/lots-login/')
def deed_check(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)

    # Delete last Review(s), if someone hits "no, go back" on deny page.
    denied_apps = ApplicationStatus.objects.filter(application__id=application_status.application.id)
    # Reset ApplicationStatus, if some hits "no, go back" on deny page.
    for a in denied_apps:
        Review.objects.filter(application=a, step_completed=2).delete()
        step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['deed'], public_status='approved', step=2)
        a.current_step = step
        a.denied = False
        a.save()

    return render(request, 'deed_check.html', {
        'application_status': application_status
        })

@login_required(login_url='/lots-login/')
def deed_check_submit(request, application_id):
    if request.method == 'POST':
        application_status = ApplicationStatus.objects.get(id=application_id)
        user = request.user
        name = request.POST.get('name', 'off')
        address = request.POST.get('address', 'off')
        church = request.POST.get('church')
        # Move to step 3 of review process.
        if (name == 'on' and address == 'on' and church == '2'):
            # If applicant applied for another lot, then also move that ApplicationStatus to Step 3.
            apps = ApplicationStatus.objects.filter(application__id=application_status.application.id)

            for app in apps:
                step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['location'], public_status='approved', step=3)
                app.current_step = step
                app.save()

                review = Review(reviewer=user, email_sent=False, application=app, step_completed=2)
                review.save()

            return HttpResponseRedirect('/application-review/step-3/%s/' % application_status.id)
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
            review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=application_status, step_completed=2)
            review.save()

            application_status.denied = True
            application_status.save()

            # If applicant applied for another lot, then also deny that ApplicationStatus.
            other_app = ApplicationStatus.objects.filter(application__id=application_status.application.id).exclude(id=application_status.id)

            if other_app:
                app = other_app[0]

                review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=app, step_completed=2)
                review.save()

                app.denied = True
                app.current_step = None
                app.save()

                send_email(request, app, "deny")

            return HttpResponseRedirect('/deny-application/%s/' % application_status.id)

@login_required(login_url='/lots-login/')
def location_check(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    # Delete last ReviewStatus, if someone hits "no, go back" on deny page.
    Review.objects.filter(application=application_status, step_completed=3).delete()
    application_status.denied = False
    application_status.save()
    # Location of the applicant's property.
    owned_pin = application_status.application.owned_pin

    # Location of the lot.
    lot_pin = application_status.lot.pin

    return render(request, 'location_check.html', {
        'application_status': application_status,
        'owned_pin': owned_pin,
        'lot_pin': lot_pin
        })

@login_required(login_url='/lots-login/')
def location_check_submit(request, application_id):
    if request.method == 'POST':
        application_status = ApplicationStatus.objects.get(id=application_id)
        user = request.user
        block = request.POST.get('block')

        if (block == 'yes'):
            # Create a new review for completing this step.
            review = Review(reviewer=user, email_sent=False, application=application_status, step_completed=3)
            review.save()

            # Are there other applicants who applied to this property?
            lot_pin = application_status.lot.pin
            other_applicants = ApplicationStatus.objects.filter(lot=lot_pin, denied=False)
            applicants_list = list(other_applicants)

            if (len(applicants_list) > 1):
                # If there are other applicants: move application to Step 4.
                step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['multi'], public_status='approved', step=4)
                application_status.current_step = step
                application_status.save()

                return HttpResponseRedirect(reverse('lots_admin'))
            else:
                # No other applicants: move application to Step 6.
                step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='approved', step=6)
                application_status.current_step = step
                application_status.save()

                return HttpResponseRedirect(reverse('lots_admin'))
        else:
            # Deny application, since applicant does not live on same block as lot.
            reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['block'])
            rev_status = Review(reviewer=user, email_sent=True, denial_reason=reason, application=application_status, step_completed=3)
            rev_status.save()
            application_status.denied = True
            application_status.save()

            return HttpResponseRedirect('/deny-application/%s/' % application_status.id)

@login_required(login_url='/lots-login/')
def multiple_applicant_check(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)

     # Delete last ReviewStatus, if someone hits "no, go back" on deny page.
    Review.objects.filter(application=application_status, step_completed=4).delete()
    application_status.denied = False
    application_status.save()

    # Location of the applicant's property.
    owned_pin = application_status.application.owned_pin

    # Location of the lot.
    lot_pin = application_status.lot.pin

    # Are there other applicants on this property?
    other_applicants = ApplicationStatus.objects.filter(lot=lot_pin, denied=False)
    applicants_list = list(other_applicants)

    # Location(s) of properties of other applicants who applied for the same property.
    other_owned_pins = [s.application.owned_pin for s in applicants_list ]
    other_owned_pins.remove(owned_pin)

    return render(request, 'multiple_applicant_check.html', {
        'application_status': application_status,
        'owned_pin': owned_pin,
        'lot_pin': lot_pin,
        'applicants_list': applicants_list,
        'other_owned_pins': other_owned_pins
        })

@login_required(login_url='/lots-login/')
def multiple_location_check_submit(request, application_id):
    if request.method == 'POST':
        user = request.user
        applications = request.POST.getlist('multi-check')
        application_ids = [int(i) for i in applications]

        applications = ApplicationStatus.objects.filter(id__in=application_ids)

        if(len(applications) > 1):
            # Move applicants to lottery.
            for a in applications:
                step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['lottery'], public_status='approved', step=5)
                a.current_step = step
                a.save()
                review = Review(reviewer=user, email_sent=True, application=a, step_completed=4)
                review.save()

                # Send lottery applicants an email notification.
                send_email(request, a, "lottery")

        else:
            # Move winning application to Step 6.
            step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='approved', step=6)
            a = ApplicationStatus.objects.get(id=application_ids[0])
            a.current_step = step
            a.save()
            review = Review(reviewer=user, email_sent=False, application=a, step_completed=4)
            review.save()

        # Deny unchecked applications.
        application_status = ApplicationStatus.objects.get(id=application_id)
        lot_pin = application_status.lot.pin
        applicants_to_deny = ApplicationStatus.objects.filter(lot=lot_pin, denied=False).exclude(id__in=application_ids)

        for a in applicants_to_deny:
            reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['adjacent'])
            review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=a, step_completed=4)
            review.save()
            a.denied = True
            a.current_step = None
            a.save()

            send_email(request, a, "deny")

        return HttpResponseRedirect(reverse('lots_admin'))


@login_required(login_url='/lots-login/')
def lottery(request):
    # Get all applications that will go to lottery.
    applications = ApplicationStatus.objects.filter(current_step__step=5)
    applications_list = list(applications)
    # Get all lots.
    lots = []
    for a in applications_list:
        lots.append(a.lot)
    # Deduplicate applied_pins array.
    lots_list = list(set(lots))

    return render(request, 'lottery.html', {
        'applications': applications,
        'lots_list': lots_list
        })

@login_required(login_url='/lots-login/')
def lottery_submit(request):
    if request.method == 'POST':
        user = request.user
        winners = [value for name, value in request.POST.items()
                if name.startswith('winner')]
        winners_id = [int(a) for a in winners]
        winning_apps = ApplicationStatus.objects.filter(id__in=winners_id)

        # Move lottery winners to Step 6.
        for a in winning_apps:
            # Move each application to Step 6.
            step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='approved', step=6)
            a.current_step = step
            a.save()

            # Create a review.
            review = Review(reviewer=user, email_sent=False, application=a, step_completed=5)
            review.save()

        # Deny lottery losers: find all applications on Step 5.
        losing_apps = ApplicationStatus.objects.filter(current_step__step=5)
        for a in losing_apps:
            # Deny each application.
            reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['lottery'])
            review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=a, step_completed=5)
            review.save()
            a.denied = True
            a.current_step = None
            a.save()

            send_email(request, a, "deny")

        return HttpResponseRedirect(reverse('lots_admin'))

@login_required(login_url='/lots-login/')
def review_EDS(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    return render(request, 'review_EDS.html', {
        'application_status': application_status
        })


@login_required(login_url='/lots-login/')
def review_status_log(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    reviews = Review.objects.filter(application=application_status)
    status = ApplicationStep.objects.all()
    return render(request, 'review_status_log.html', {
        'application_status': application_status,
        'reviews': reviews,
        'status': status
        })

@login_required(login_url='/lots-login/')
def alderman_advance_submit(request):
    if request.method == 'POST':
        user = request.user
        supported_app_ids = request.POST.getlist('letter-received')
        supported_app_ids = [int(i) for i in supported_app_ids]

        applications = ApplicationStatus.objects.filter(id__in=supported_app_ids)

        for a in applications:
            # Move each application to Step 7.
            step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['EDS'], public_status='approved', step=7)
            a.current_step = step
            a.save()

            # Create a review.
            review = Review(reviewer=user, email_sent=False, application=a, step_completed=6)
            review.save()

        return HttpResponseRedirect(reverse('lots_admin'))

def send_email(request, application_status, email_type):
    app = application_status.application
    lot = application_status.lot
    review = Review.objects.filter(application=application_status).latest('id')

    context = Context({'app': app, 'review': review, 'lot': lot, 'DENIAL_REASONS': DENIAL_REASONS, 'host': request.get_host()})
    html = email_type + "_html_email.html"
    txt = email_type + "_text_email.txt"
    html_template = get_template(html)
    text_template = get_template(txt)
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

