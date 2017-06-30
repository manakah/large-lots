from datetime import datetime
import csv
import json
import re
from collections import namedtuple

from operator import __or__ as OR
from functools import reduce
from datetime import datetime
from django import forms

from esridump.dumper import EsriDumper
from esridump.errors import EsriDownloadError

from raven.contrib.django.raven_compat.models import client

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import connection, connections
from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse, \
    HttpResponseNotFound
from django.conf import settings
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django import forms
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
                return HttpResponseRedirect(reverse('lots_admin', args=['all']))
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

    applied_count = len(applied_pins)
    pins_str = ",".join(["'%s'" % a.replace('-','').replace(' ','') for a in applied_pins])

    return render(request, 'admin-map.html', {
        'applied_count': applied_count,
        'applied_pins': pins_str
        })

@login_required(login_url='/lots-login/')
def lots_admin(request, step):
    query = request.GET.get('search_box', None)
    page = request.GET.get('page', None)

    # Add session variables for easy return to search results after step 3 and denials.
    request.session['page'] = page
    request.session['query'] = query

    with connection.cursor() as cursor:
        # Order by last name ascending by default.
        order_by = request.GET.get('order_by', 'last_name')
        sort_order = request.GET.get('sort_order', 'asc')

        if order_by == 'ward':
            order_by = 'ward::int'

        toggle_order = 'asc'
        if sort_order.lower() == 'asc':
            toggle_order = 'desc'

        # Variables: list of step specific, denied, and all.
        if step.isdigit():
            step = int(step)

            sql = '''
            SELECT
                lots_admin_applicationstatus.id as status_id,
                lots_admin_application.id as app_id, lots_admin_application.received_date,
                lots_admin_application.first_name, lots_admin_application.last_name,
                lots_admin_application.organization, lots_admin_application.tracking_id,
                lots_admin_applicationstep.public_status, lots_admin_applicationstep.step,
                lots_admin_applicationstep.description as step_description,
                lots_admin_lot.address_id, lots_admin_lot.pin,
                lots_admin_address.street, lots_admin_address.ward
            FROM lots_admin_applicationstatus
            LEFT JOIN lots_admin_application
            ON lots_admin_applicationstatus.application_id=lots_admin_application.id
            LEFT JOIN lots_admin_applicationstep
            ON lots_admin_applicationstatus.current_step_id=lots_admin_applicationstep.id
            LEFT JOIN lots_admin_lot
            ON lots_admin_applicationstatus.lot_id=lots_admin_lot.pin
            LEFT JOIN lots_admin_address
            ON lots_admin_lot.address_id=lots_admin_address.id
            WHERE lots_admin_applicationstep.step={0}
            AND coalesce(deed_image, '') <> ''
            '''.format(step, order_by, sort_order)

            if query:
                sql += " AND plainto_tsquery('english', '{0}') @@ to_tsvector(lots_admin_application.first_name || ' ' || lots_admin_application.last_name || ' ' || lots_admin_address.ward) ORDER BY {1} {2}".format(query, order_by, sort_order)

            else:
                sql += " ORDER BY {0} {1}".format(order_by, sort_order)

        elif step == "denied":

            sql = '''
            SELECT
                lots_admin_applicationstatus.id as status_id,
                lots_admin_applicationstatus.denied,
                lots_admin_application.id as app_id, lots_admin_application.received_date,
                lots_admin_application.first_name, lots_admin_application.last_name,
                lots_admin_application.organization, lots_admin_application.tracking_id,
                lots_admin_applicationstep.public_status, lots_admin_applicationstep.step,
                lots_admin_applicationstep.description as step_description,
                lots_admin_lot.address_id, lots_admin_lot.pin,
                lots_admin_address.street, lots_admin_address.ward
            FROM lots_admin_applicationstatus
            LEFT JOIN lots_admin_application
            ON lots_admin_applicationstatus.application_id=lots_admin_application.id
            LEFT JOIN lots_admin_applicationstep
            ON lots_admin_applicationstatus.current_step_id=lots_admin_applicationstep.id
            LEFT JOIN lots_admin_lot
            ON lots_admin_applicationstatus.lot_id=lots_admin_lot.pin
            LEFT JOIN lots_admin_address
            ON lots_admin_lot.address_id=lots_admin_address.id
            WHERE lots_admin_applicationstatus.denied=True
            AND coalesce(deed_image, '') <> ''
            '''

            if query:
                sql += " AND plainto_tsquery('english', '{0}') @@ to_tsvector(lots_admin_application.first_name || ' ' || lots_admin_application.last_name || ' ' || lots_admin_address.ward) ORDER BY {1} {2}".format(query, order_by, sort_order)

            else:
                sql += " ORDER BY {0} {1}".format(order_by, sort_order)

        elif step == "all":

            sql = '''
            SELECT
                lots_admin_applicationstatus.id as status_id,
                lots_admin_application.id as app_id, lots_admin_application.received_date,
                lots_admin_application.first_name, lots_admin_application.last_name,
                lots_admin_application.organization, lots_admin_application.tracking_id,
                lots_admin_applicationstep.public_status, lots_admin_applicationstep.step,
                lots_admin_applicationstep.description as step_description,
                lots_admin_lot.address_id, lots_admin_lot.pin,
                lots_admin_address.street, lots_admin_address.ward
            FROM lots_admin_applicationstatus
            LEFT JOIN lots_admin_application
            ON lots_admin_applicationstatus.application_id=lots_admin_application.id
            LEFT JOIN lots_admin_applicationstep
            ON lots_admin_applicationstatus.current_step_id=lots_admin_applicationstep.id
            LEFT JOIN lots_admin_lot
            ON lots_admin_applicationstatus.lot_id=lots_admin_lot.pin
            LEFT JOIN lots_admin_address
            ON lots_admin_lot.address_id=lots_admin_address.id
            '''

            if query:
                sql += " WHERE plainto_tsquery('english', '{0}') @@ to_tsvector(lots_admin_application.first_name || ' ' || lots_admin_application.last_name || ' ' || lots_admin_address.ward) ORDER BY {1} {2}".format(query, order_by, sort_order)

            else:
                sql += " ORDER BY {0} {1}".format(order_by, sort_order)


        cursor.execute(sql)
        columns = [c[0] for c in cursor.description]
        result_tuple = namedtuple('ApplicationStatus', columns)
        application_status_list = [result_tuple(*r) for r in cursor]

        step2 = Q(current_step__step=2)
        step3 = Q(current_step__step=3)
        step4 = Q(current_step__step=4)
        step5 = Q(current_step__step=5)
        step6 = Q(current_step__step=6)
        before_step4 = ApplicationStatus.objects.filter(step2 | step3)
        on_steps234 = ApplicationStatus.objects.filter(step2 | step3 | step4)
        on_steps23456 = ApplicationStatus.objects.filter(step2 | step3 | step4 | step5 | step6)
        app_count = len(ApplicationStatus.objects.all())

    counter_range = range(2, 12)

    paginator = Paginator(application_status_list, 20)

    try:
        application_status_list = paginator.page(page)
    except PageNotAnInteger:
        application_status_list = paginator.page(1)
    except EmptyPage:
        application_status_list = paginator.page(paginator.num_pages)

    return render(request, 'admin.html', {
        'application_status_list': application_status_list,
        'selected_pilot': settings.CURRENT_PILOT,
        'pilot_info': settings.PILOT_INFO,
        'before_step4': before_step4,
        'on_steps234': on_steps234,
        'on_steps23456': on_steps23456,
        'app_count': app_count,
        'step': step,
        'counter_range': counter_range,
        'order_by': order_by,
        'toggle_order': toggle_order
        })

@login_required(login_url='/lots-login/')
def csv_dump(request, pilot, status):
    response = HttpResponse(content_type='text/csv')
    now = datetime.now().isoformat()
    response['Content-Disposition'] = 'attachment; filename=Large_Lots_Applications_%s_%s.csv' % (pilot, now)

    if status == 'all':
        applications = ApplicationStatus.objects.filter(application__pilot=pilot)
    elif status == 'denied':
        applications = ApplicationStatus.objects.filter(application__pilot=pilot).filter(denied=True)
    else:
        applications = ApplicationStatus.objects.filter(application__pilot=pilot).filter(current_step__step=status)

    header = [
        'ID',
        'Current application step',
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
        'Ward',
        'Community',
        'Lot Image URL',
        'Lot Planned Use',
    ]

    rows = []
    for application_status in applications:
        owned_address = '%s %s %s %s' % \
            (getattr(application_status.application.owned_address, 'street', ''),
            getattr(application_status.application.owned_address, 'city', ''),
            getattr(application_status.application.owned_address, 'state', ''),
            getattr(application_status.application.owned_address, 'zip_code', ''))
        contact_address = '%s %s %s %s' % \
            (getattr(application_status.application.contact_address, 'street', ''),
            getattr(application_status.application.contact_address, 'city', ''),
            getattr(application_status.application.contact_address, 'state', ''),
            getattr(application_status.application.contact_address, 'zip_code', ''))

        addr = getattr(application_status.lot.address, 'street', '').upper()
        addr_full = '%s %s %s %s' % \
            (getattr(application_status.lot.address, 'street', ''),
            getattr(application_status.lot.address, 'city', ''),
            getattr(application_status.lot.address, 'state', ''),
            getattr(application_status.lot.address, 'zip_code', ''))
        pin = application_status.lot.pin[:-4]
        ward = application_status.lot.address.ward
        community = application_status.lot.address.community
        image_url = 'https://pic.datamade.us/%s.jpg' % application_status.lot.pin.replace('-', '')
        lot_use = application_status.lot.planned_use

        try:
            deed_image = application_status.application.deed_image.url
        except ValueError:
            deed_image = None


        if application_status.current_step:
            current_step = str(application_status.current_step.step) + ': ' + str(application_status.current_step)
        else:
            current_step = 'Denied'

        rows.append([
            application_status.application.id,
            current_step,
            application_status.application.received_date.strftime('%Y-%m-%d %H:%m %p'),
            application_status.application.first_name,
            application_status.application.last_name,
            application_status.application.organization,
            getattr(application_status.application.owned_address, 'street', '').upper(),
            owned_address,
            application_status.application.owned_pin,
            deed_image,
            contact_address,
            application_status.application.phone,
            application_status.application.email,
            application_status.application.how_heard,
            pin,
            addr,
            addr_full,
            ward,
            community,
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
    review             = Review.objects.filter(application=application_status).latest('id')
    warning            = None

    # Check if application has been denied and has a current step of None.
    if application_status.current_step is None:
        warning = 'Denied'

    return render(request, 'deny_application.html', {
        'application_status': application_status,
        'review': review,
        'warning': warning,
        })

@login_required(login_url='/lots-login/')
def deny_submit(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    application_status.current_step = None
    application_status.save()

    send_email(request, application_status)

    page = request.session['page']
    query = request.session['query']
    path = '?'

    if page:
        path += 'page={}&'.format(page)
    if query:
        path += 'search_box={}'.format(query)

    clean_path = path.rstrip('?').rstrip('&')

    return HttpResponseRedirect('/lots-admin/all/%s' % clean_path )
    # return HttpResponseRedirect(reverse('lots_admin', args=["all"]))

@login_required(login_url='/lots-login/')
def double_submit(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)

    return render(request, 'double_submit.html', {
        'application_status': application_status,
        })

@login_required(login_url='/lots-login/')
def deed_check(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    first = application_status.application.first_name
    last = application_status.application.last_name
    other_applications = Application.objects.filter(first_name=first, last_name=last)

    # Check if application has been denied and has a current step of None.
    if application_status.current_step is None:
        warning = 'Denied'
    # If not, then check if application has step different than the view.
    elif application_status.current_step.step != 2:
        warning = 'Reviewed'
    # If not the above, then delete last Review(s) and reset ApplicationStatus, since someone hit "no, go back" on deny page.
    else:
        warning = None
        Review.objects.filter(application=application_status, step_completed=2).delete()
        step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['deed'], public_status='valid', step=2)
        application_status.current_step = step
        application_status.denied = False
        application_status.save()

    return render(request, 'deed_check.html', {
        'application_status': application_status,
        'other_applications': other_applications,
        'warning': warning,
        })

@login_required(login_url='/lots-login/')
def deed_check_submit(request, application_id):
    if request.method == 'POST':
        application_status = ApplicationStatus.objects.get(id=application_id)
        user = request.user
        document = request.POST.get('document')
        name = request.POST.get('name', 'off')
        address = request.POST.get('address', 'off')
        church = request.POST.get('church')

        # Check if application has already been denied.
        if application_status.current_step == None:
            return HttpResponseRedirect('/double-submit/%s/' % application_status.id)
        # Check if application has moved past step 2.
        elif application_status.current_step.step != 2:
            return HttpResponseRedirect('/double-submit/%s/' % application_status.id)
        # Move to step 3 of review process.
        elif (name == 'on' and address == 'on' and church == '2' and document == '2'):
            step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['location'], public_status='valid', step=3)
            application_status.current_step = step
            application_status.save()

            review = Review(reviewer=user, email_sent=False, application=application_status, step_completed=2)
            review.save()

            return HttpResponseRedirect('/application-review/step-3/%s/' % application_status.id)
        # Deny application.
        else:
            if (document == '1'):
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['document'])
            elif (church == '1'):
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['church'])
            elif (name == 'off' and address == 'on'):
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['name'])
            elif (name == 'on' and address == 'off'):
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['address'])
            else:
                reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['nameaddress'])
            review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=application_status, step_completed=2)
            review.save()

            application_status.denied = True
            application_status.save()

            # REMOVE THIS STEP. It may be causing issues.
            # If applicant applied for another lot, then also deny that ApplicationStatus.
            # other_app = ApplicationStatus.objects.filter(application__id=application_status.application.id).exclude(id=application_status.id)

            # if other_app:
            #     app = other_app[0]

            #     review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=app, step_completed=2)
            #     review.save()

            #     app.denied = True
            #     app.current_step = None
            #     app.save()

            return HttpResponseRedirect('/deny-application/%s/' % application_status.id)

@login_required(login_url='/lots-login/')
def deed_duplicate_submit(request, application_id):
    if request.method == 'POST':
        application_status = ApplicationStatus.objects.get(id=application_id)
        user = request.user

        reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['deedoveruse'])
        review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=application_status, step_completed=2)
        review.save()

        application_status.denied = True
        application_status.save()

        return HttpResponseRedirect('/deny-application/%s/' % application_status.id)

@login_required(login_url='/lots-login/')
def applicant_duplicate_submit(request, application_id):
    if request.method == 'POST':
        application_status = ApplicationStatus.objects.get(id=application_id)
        user = request.user

        reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['duplicate'])
        review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=application_status, step_completed=2)
        review.save()

        application_status.denied = True
        application_status.save()

        return HttpResponseRedirect('/deny-application/%s/' % application_status.id)

@login_required(login_url='/lots-login/')
def location_check(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)

    # Check if application has been denied and has a current step of None.
    if application_status.current_step is None:
        warning = 'Denied'
    # If not, then check if application has step different than the view.
    elif application_status.current_step.step != 3:
        warning = 'Reviewed'
    # If not the above, then delete last Review(s) and reset ApplicationStatus, since someone hit "no, go back" on deny page.
    else:
        warning = None
        # Delete last ReviewStatus, if someone hits "no, go back" on deny page.
        Review.objects.filter(application=application_status, step_completed=3).filter(application__denied=True).delete()
        application_status.denied = False
        application_status.save()

    # Location of the applicant's property.
    owned_pin = application_status.application.owned_pin

    # Location of the lot.
    lot_pin = application_status.lot.pin

    step2 = Q(current_step__step=2)
    step3 = Q(current_step__step=3)
    before_step4 = ApplicationStatus.objects.filter(step2 | step3)

    return render(request, 'location_check.html', {
        'application_status': application_status,
        'owned_pin': owned_pin,
        'lot_pin': lot_pin,
        'warning': warning,
        'before_step4': before_step4,
        })

# @login_required(login_url='/lots-login/')
def get_parcel_geometry(request):
    pin = request.GET.get('pin')

    if pin:
        query_args = {'f': 'json', 'outSR': 4326, 'where': 'PIN14={}'.format(pin)}
        dumper = EsriDumper('http://cookviewer1.cookcountyil.gov/arcgis/rest/services/cookVwrDynmc/MapServer/44',
                            extra_query_args=query_args)

        try:
            geometry = list(dumper)[0]
            response = HttpResponse(json.dumps(geometry), content_type='application/json')
        except (EsriDownloadError, StopIteration, IndexError) as e:
            resp = {'status': 'error', 'message': "PIN '{}' could not be found".format(pin)}
            response = HttpResponseNotFound(json.dumps(resp), content_type='application/json')
        except Exception as e:
            client.captureException()
            resp = {'status': 'error', 'message': "Unknown error occured '{}'".format(str(e))}
            response = HttpResponse(json.dumps(resp), content_type='application/json')
            response.status_code = 500
    else:
        resp = {'status': 'error', 'message': "'pin' is a required parameter"}
        response = HttpResponse(json.dumps(resp), content_type='application/json')
        response.status_code = 400

    return response

@login_required(login_url='/lots-login/')
def location_check_submit(request, application_id):
    if request.method == 'POST':
        application_status = ApplicationStatus.objects.get(id=application_id)
        user = request.user
        block = request.POST.get('block')
        # Get values for Redirect
        page = request.session['page']
        query = request.session['query']
        path = '?'

        if page:
            path += 'page={}&'.format(page)
        if query:
            path += 'search_box={}'.format(query)

        clean_path = path.rstrip('?').rstrip('&')

       # Check if application has already been denied.
        if application_status.current_step == None:
            return HttpResponseRedirect('/double-submit/%s/' % application_status.id)
        # Check if application has moved past step 2.
        elif application_status.current_step.step != 3:
            return HttpResponseRedirect('/double-submit/%s/' % application_status.id)
        elif block == 'yes':
            # Create a new review for completing this step.
            review = Review(reviewer=user, email_sent=False, application=application_status, step_completed=3)
            review.save()

            # Are there other applicants who applied to this property?
            lot_pin = application_status.lot.pin
            other_applicants = ApplicationStatus.objects.filter(lot=lot_pin, denied=False)
            applicants_list = list(other_applicants)

            if (len(applicants_list) > 1):
                # If there are other applicants: move application to Step 4.
                step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['multi'], public_status='valid', step=4)
                application_status.current_step = step
                application_status.save()

                return HttpResponseRedirect('/lots-admin/all/%s' % clean_path )
            else:
                # Move to Step 5: Adlerman letter.
                step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='valid', step=5)
                application_status.current_step = step
                application_status.save()

                return HttpResponseRedirect('/lots-admin/all/%s' % clean_path )
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
    warning = None
    application_status = ApplicationStatus.objects.get(id=application_id)

     # Delete last ReviewStatus, if someone hits "no, go back" on deny page.
    Review.objects.filter(application=application_status, step_completed=4).filter(application__denied=True).delete()
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

    if application_status.current_step:
        if application_status.current_step.step != 4:
            warning = 'Application already reviewed.'

    return render(request, 'multiple_applicant_check.html', {
        'application_status': application_status,
        'owned_pin': owned_pin,
        'lot_pin': lot_pin,
        'applicants_list': applicants_list,
        'other_owned_pins': other_owned_pins,
        'warning': warning,
        })

@login_required(login_url='/lots-login/')
def multiple_location_check_submit(request, application_id):
    if request.method == 'POST':
        user = request.user
        applications = request.POST.getlist('multi-check')
        application_ids = [int(i) for i in applications]

        applications = ApplicationStatus.objects.filter(id__in=application_ids)

        # Get values for Redirect
        page = request.session['page']
        query = request.session['query']
        path = '?'

        if page:
            path += 'page={}&'.format(page)
        if query:
            path += 'search_box={}'.format(query)

        clean_path = path.rstrip('?').rstrip('&')

        if(len(applications) > 1):
            # Tag application with lottery boolean.
            for a in applications:
                a.lottery = True
                a.save()

                step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='valid', step=5)
                a.current_step = step
                a.save()
                review = Review(reviewer=user, email_sent=False, application=a, step_completed=4)
                review.save()

        else:
        # Move winning application to Aldermanic review.
            if applications:
                step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='valid', step=5)
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

            send_email(request, a)

        return HttpResponseRedirect('/lots-admin/all/%s' % clean_path )

@login_required(login_url='/lots-login/')
def lotteries(request):
    # Get all applications that will go to lottery.
    applications = ApplicationStatus.objects.filter(current_step__step=6).order_by('application__last_name')
    applications_list = list(applications)
    # Get all lots.
    lots = []
    for a in applications_list:
        lots.append(a.lot)
    # Deduplicate applied_pins array.
    lots_list = list(set(lots))

    return render(request, 'lotteries.html', {
        'lots_list': lots_list,
        })

@login_required(login_url='/lots-login/')
def lottery(request, lot_pin):
    lot = Lot.objects.get(pin=lot_pin)

    applications = ApplicationStatus.objects.filter(current_step__step=6).filter(lot=lot_pin).order_by('application__last_name')
    applications_list = list(applications)

    return render(request, 'lottery.html', {
        'applications': applications,
        'lot': lot,
        })

@login_required(login_url='/lots-login/')
def lottery_submit(request, lot_pin):
    if request.method == 'POST':
        user = request.user
        winner = [value for name, value in request.POST.items()
                if name.startswith('winner')]
        winner_id = int(winner[0])
        winning_app = ApplicationStatus.objects.get(id=winner_id)

        # Move lottery winner to Step 7.
        step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['EDS_waiting'], public_status='valid', step=7)
        winning_app.current_step = step
        winning_app.save()

        # Create a review.
        review = Review(reviewer=user, email_sent=False, application=winning_app, step_completed=6)
        review.save()

        # Deny lottery losers: find all applications on Step 5.
        losing_apps = ApplicationStatus.objects.filter(current_step__step=6).filter(lot=lot_pin)
        for a in losing_apps:
            # Deny each application.
            reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['lottery'])
            review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=a, step_completed=6)
            review.save()
            a.denied = True
            a.current_step = None
            a.save()

            send_email(request, a)

        return HttpResponseRedirect(reverse('lotteries'))


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
def bulk_submit(request):
    if request.method == 'POST':
        user = request.user
        selected_step = request.POST.getlist('step')[0]
        step_arg = re.sub('step', '', selected_step)
        selected_apps = request.POST.getlist('letter-received')
        selected_app_ids = [int(i) for i in selected_apps]
        applications = ApplicationStatus.objects.filter(id__in=selected_app_ids)

        for a in applications:
            if selected_step == 'step5':
                # Check if applicant goes to lottery.
                if a.lottery == True:
                    # Move applicantion to step 6: lottery.
                    l = 'lottery', 'valid', 6, a
                    next_step(*l)

                    # Create a review.
                    review = Review(reviewer=user, email_sent=False, application=a, step_completed=5)
                    review.save()
                else:
                    # Move application to step 7.
                    l = 'EDS_waiting', 'valid', 7, a
                    next_step(*l)

                    # Create a review.
                    review = Review(reviewer=user, email_sent=False, application=a, step_completed=5)
                    review.save()
            # Note: moving from step 7 (EDS_waiting) to step 8 (EDS_submission) happens automatically.
            elif selected_step == 'step8':
                 # Move application to step 9.
                l = 'debts', 'valid', 9, a
                next_step(*l)

                # Create a review.
                review = Review(reviewer=user, email_sent=False, application=a, step_completed=8)
                review.save()
            elif selected_step == 'step9':
                # Move application to step 10.
                l = 'commission', 'valid', 10, a
                next_step(*l)

                # Create a review.
                review = Review(reviewer=user, email_sent=False, application=a, step_completed=9)
                review.save()
            elif selected_step == 'step10':
                # Move application to step 11.
                l = 'city_council', 'valid', 11, a
                next_step(*l)

                # Create a review.
                review = Review(reviewer=user, email_sent=False, application=a, step_completed=10)
                review.save()
            elif selected_step == 'step11':
                print("herereeee!")
                 # Move application to step 12.
                l = 'sold', 'valid', 12, a
                next_step(*l)

                # Create a review.
                review = Review(reviewer=user, email_sent=False, application=a, step_completed=11)
                review.save()
            elif selected_step == 'deny':
                # Redirect to bulk deny view. Save application ids in session.
                request.session['application_ids'] = selected_app_ids
                return HttpResponseRedirect('/bulk-deny')
            else:
                return HttpResponseRedirect(reverse('lots_admin', args=['all']))

        return HttpResponseRedirect(reverse('lots_admin', args=['all']))

@login_required(login_url='/lots-login/')
def bulk_deny(request):
    app_ids = request.session['application_ids']
    applications = ApplicationStatus.objects.filter(id__in=app_ids)

    return render(request, 'bulk_deny.html', {
        'applications': applications
        })

@login_required(login_url='/lots-login/')
def bulk_deny_submit(request):
    user = request.user
    denial_reasons = request.POST.getlist('denial-reason')
    no_deny_ids = request.POST.getlist('remove')
    apps = request.POST.getlist('application')
    app_ids = [int(i) for i in apps]

    dictionary = dict(zip(app_ids, denial_reasons))
    apps_to_deny = ApplicationStatus.objects.filter(id__in=app_ids).exclude(id__in=no_deny_ids)

    for a in apps_to_deny:
        dict_reason = dictionary[a.id]
        reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS[dict_reason])

        review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=a)
        review.save()
        a.denied = True
        a.current_step = None
        a.save()

        send_email(request, a)

    return HttpResponseRedirect(reverse('lots_admin', args=['all']))

@login_required(login_url='/lots-login/')
def status_tally(request):
    total = ApplicationStatus.objects.all()
    # Order by ward.
    step2 = ApplicationStatus.objects.filter(current_step__step=2)
    step3 = ApplicationStatus.objects.filter(current_step__step=3)
    step4 = ApplicationStatus.objects.filter(current_step__step=4)
    step5 = ApplicationStatus.objects.filter(current_step__step=5)
    step6 = ApplicationStatus.objects.filter(current_step__step=6)
    step7 = ApplicationStatus.objects.filter(current_step__step=7)
    step8 = ApplicationStatus.objects.filter(current_step__step=8)
    step9 = ApplicationStatus.objects.filter(current_step__step=9)
    step10 = ApplicationStatus.objects.filter(current_step__step=10)
    step11 = ApplicationStatus.objects.filter(current_step__step=11)
    sold = ApplicationStatus.objects.filter(current_step__step=12)
    denied = ApplicationStatus.objects.filter(denied=True)

    return render(request, 'status-tally.html', {
        'total': total,
        'step2': step2,
        'step3': step3,
        'step4': step4,
        'step5': step5,
        'step6': step6,
        'step7': step7,
        'step8': step8,
        'step9': step9,
        'step10': step10,
        'step11': step11,
        'sold': sold,
        'denied': denied
        })

def next_step(description_key, status, step_int, application):
        step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS[description_key], public_status=status, step=step_int)
        application.current_step = step
        application.save()

def send_email(request, application_status):
    app = application_status.application
    lot = application_status.lot
    review = Review.objects.filter(application=application_status).latest('id')
    today = datetime.now().date()

    context = Context({'app': app, 'review': review, 'lot': lot, 'DENIAL_REASONS': DENIAL_REASONS, 'host': request.get_host(), 'today': today})
    html = "deny_html_email.html"
    txt = "deny_text_email.txt"
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

@login_required(login_url='/lots-login/')
def deed(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)

    return render(request, 'deed.html', {
        'application_status': application_status,
        })

