from datetime import datetime
import csv
import json
import re
from collections import namedtuple
from smtplib import SMTPException
from io import StringIO

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
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User
from django import forms
from django.template import Context
from django.template.loader import get_template
from django.db.models import Q
from django.core.exceptions import MultipleObjectsReturned
from django.views.generic.base import TemplateView

from .look_ups import DENIAL_REASONS, APPLICATION_STATUS
from .utils import create_email_msg, send_denial_email, create_redirect_path, \
    step_from_status
from lots_admin.models import Application, Lot, ApplicationStep, Address, \
    Review, ApplicationStatus, DenialReason, PrincipalProfile, LotUse, UpdatedEntity
from lots_admin.forms import AddressUpdateForm, ApplicationUpdateForm, DateTimeForm, \
    EdsEmailForm, FinalEdsEmailForm, EdsDenialEmailForm, LotteryEmailForm, ClosingTimeEmail, CustomEmail

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
def lots_admin_principal_profiles(request):
    applications = Application.objects.filter(principalprofile__isnull=False).distinct()

    sql = '''
        SELECT
          SUM(CASE WHEN (deleted_at is null) THEN 1 ELSE 0 END) AS available,
          SUM(CASE WHEN (exported_at is null) THEN 1 ELSE 0 END) AS not_exported,
          MAX(exported_at) AS last_export,
          MAX(deleted_at) AS last_delete
        FROM lots_admin_principalprofile
    '''

    with connection.cursor() as cursor:
        cursor.execute(sql)
        ppf_meta, = (row for row in cursor)
        available, not_exported, last_export, last_delete = ppf_meta

    return render(request, 'admin-principal-profiles.html', {
            'selected_pilot': settings.CURRENT_PILOT,
            'application_count': len(applications),
            'available_count': available,
            'not_exported_count': not_exported,
            'last_export': last_export,
            'last_delete': last_delete,
        })

@login_required(login_url='/lots-login/')
def lots_admin(request, step):
    query = request.GET.get('query', None)
    page = request.GET.get('page', None)

    # Add session variables for easy return to search results after step 3 and denials.
    request.session['page'] = page
    request.session['query'] = query

    sql_fmt = '''
        SELECT
          app.id as app_id,
          app.received_date,
          app.first_name,
          app.last_name,
          app.organization,
          app.organization_confirmed,
          app.tracking_id,
          app.ppf_received,
          app.eds_received,
          status.id as status_id,
          status.denied,
          step.public_status,
          step.step,
          step.description as step_description,
          lot.address_id,
          lot.pin,
          address.street,
          address.ward
        FROM lots_admin_applicationstatus AS status
        LEFT JOIN lots_admin_application AS app
        ON status.application_id = app.id
        LEFT JOIN lots_admin_applicationstep AS step
        ON status.current_step_id = step.id
        LEFT JOIN lots_admin_lot AS lot
        ON status.lot_id = lot.pin
        LEFT JOIN lots_admin_address AS address
        ON lot.address_id = address.id
        {conditions}
        {order_by}
    '''

    if step.isdigit():
        step = int(step)

        conditions = '''
            WHERE coalesce(deed_image, '') <> ''
            AND step = {0}
        '''.format(step)

        if request.GET.get('eds', None):
            conditions += 'AND app.eds_received = {} '.format(request.GET['eds'])

        elif request.GET.get('ppf', None):
            conditions += 'AND app.ppf_received = {} '.format(request.GET['ppf'])

    elif step == 'denied':
        conditions = '''
            WHERE coalesce(deed_image, '') <> ''
            AND status.denied = TRUE
        '''

    elif step == 'all':
        conditions = ''

    if query:
        query_sql = "plainto_tsquery('english', '{0}') @@ to_tsvector(app.first_name || ' ' || app.last_name || ' ' || address.ward)".format(query)

        if step == 'all':
            conditions = 'WHERE {0}'.format(query_sql)
        else:
            conditions += 'AND {0}'.format(query_sql)

    order_by = request.GET.get('order_by', 'last_name')
    sort_order = request.GET.get('sort_order', 'asc')

    if order_by == 'ward':
        order_by = 'ward::int'

    sql = sql_fmt.format(conditions=conditions,
                         order_by='ORDER BY {0} {1}'.format(order_by, sort_order))

    with connection.cursor() as cursor:
        cursor.execute(sql)

        columns = [col.name for col in cursor.description]
        result_tuple = namedtuple('ApplicationStatus', columns)
        application_status_list = [result_tuple(*r) for r in cursor]

    steps = {i: Q(current_step__step=i) for i in range(2, 7)}

    before_step4 = ApplicationStatus.objects.filter(steps[2] | steps[3])
    on_steps23456 = ApplicationStatus.objects.filter(steps[2] | steps[3] | steps[4] | steps[5] | steps[6])

    app_count = len(ApplicationStatus.objects.all())
    ppf_count = len(Application.objects\
                               .filter(principalprofile__isnull=False)\
                               .distinct())

    step_range = range(2, 11)

    if sort_order.lower() == 'asc':
        toggle_order = 'desc'

    else:
        toggle_order = 'asc'

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
        'on_steps23456': on_steps23456,
        'app_count': app_count,
        'ppf_count': ppf_count,
        'step': step,
        'step_range': step_range,
        'order_by': order_by,
        'toggle_order': toggle_order
        })

@login_required(login_url='/lots-login/')
def dump_applications(request, pilot, status):
    response = HttpResponse(content_type='text/csv')
    now = datetime.now().isoformat()
    response['Content-Disposition'] = 'attachment; filename=Large_Lots_Applications_%s_%s.csv' % (pilot, now)
    # Hit the database less: https://docs.djangoproject.com/en/2.0/ref/models/querysets/#select-related
    if status == 'all':
        applications = ApplicationStatus.objects.select_related('application', 'lot').filter(application__pilot=pilot)
    elif status == 'denied':
        applications = ApplicationStatus.objects.select_related('application', 'lot').filter(application__pilot=pilot).filter(denied=True)
    else:
        applications = ApplicationStatus.objects.select_related('application', 'lot').filter(application__pilot=pilot).filter(current_step__step=status)

    header = [
        'ID',
        'Current application step',
        'EDS Received',
        'PPF Received',
        'Date received',
        'First Name',
        'Last Name',
        'Organization',
        'Owned Street Number',
        'Owned Street Dir',
        'Owned Street Name',
        'Owned Street Type',
        'Owned City',
        'Owned PIN',
        'Deed Image URL',
        'Contact Address',
        'Phone',
        'Email',
        'Received assistance',
        'Lot PIN',
        'Lot Street Number',
        'Lot Street Dir',
        'Lot Street Name',
        'Lot Street Type',
        'Lot City',
        'Ward',
        'Community',
        'Lot Image URL',
        'Lot Planned Use',
    ]

    rows = []
    for application_status in applications:
        # Applicant address info
        owned_street_number = getattr(application_status.application.owned_address, 'street_number', '').upper()
        owned_street_dir = getattr(application_status.application.owned_address, 'street_dir', '').upper()
        owned_street_name = getattr(application_status.application.owned_address, 'street_name', '').upper()
        owned_street_type = getattr(application_status.application.owned_address, 'street_type', '').upper()
        owned_city = getattr(application_status.application.owned_address, 'city', '').upper()
        contact_address = '%s %s %s %s' % \
            (getattr(application_status.application.contact_address, 'street', ''),
            getattr(application_status.application.contact_address, 'city', ''),
            getattr(application_status.application.contact_address, 'state', ''),
            getattr(application_status.application.contact_address, 'zip_code', ''))
        # Lot requested info
        lot_street_number = getattr(application_status.lot.address, 'street_number', '').upper()
        lot_street_dir = getattr(application_status.lot.address, 'street_dir', '').upper()
        lot_street_name = getattr(application_status.lot.address, 'street_name', '').upper()
        lot_street_type = getattr(application_status.lot.address, 'street_type', '').upper()
        lot_city = getattr(application_status.lot.address, 'city', '').upper()
        pin = application_status.lot.pin[:-4]
        ward = application_status.lot.address.ward
        community = application_status.lot.address.community
        image_url = 'https://pic.datamade.us/%s.jpg' % application_status.lot.pin.replace('-', '')

        try:
            lot_use = LotUse.objects\
                            .filter(application=application_status.application,
                                    lot=application_status.lot)\
                            .first()\
                            .planned_use

        except AttributeError:
            lot_use = None

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
            application_status.application.eds_received,
            application_status.application.ppf_received,
            application_status.application.received_date.strftime('%Y-%m-%d %H:%m %p'),
            application_status.application.first_name,
            application_status.application.last_name,
            application_status.application.organization,
            owned_street_number,
            owned_street_dir,
            owned_street_name,
            owned_street_type,
            owned_city,
            application_status.application.owned_pin,
            deed_image,
            contact_address,
            application_status.application.phone,
            application_status.application.email,
            application_status.application.how_heard,
            pin,
            lot_street_number,
            lot_street_dir,
            lot_street_name,
            lot_street_type,
            lot_city,
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
def dump_principal_profiles(request, pilot):
    response = HttpResponse(content_type='text/csv')
    now = datetime.now().isoformat()
    response['Content-Disposition'] = 'attachment; filename=Large_Lots_Principal_Profiles_%s_%s.csv' % (pilot, now)

    def org_address(ppf):
        application = ppf.application
        if application.organization_confirmed:
            return (application.organization, application.contact_address.street)
        return (None, None)

    profiles = PrincipalProfile.objects.select_related('application', 'related_person')\
                                       .filter(application__pilot=pilot)\
                                       .filter(deleted_at__isnull=True)

    header = [
        'Department',
        'Requester',
        'Date Received',
        'Principal\'s Name',
        'Principal\'s Address',
        'Entity',
        'Address',
        'Driver\'s License Number',
        'Plate Number',
        'Social Security number',
        'Date of Birth',
    ]

    rows = []

    for profile in profiles:
        organization, organization_address = org_address(profile)
        rows.append([
            'Department of Planning and Development (DPD)',
            ('{0} {1}').format(request.user.first_name, request.user.last_name),
            profile.created_at.strftime('%Y-%m-%d %H:%m %p'),
            ('{0} {1}').format(profile.entity.first_name, profile.entity.last_name),
            profile.address,
            organization,
            organization_address,
            ('{0} {1}').format(profile.drivers_license_state, profile.drivers_license_number),
            ('{0} {1}').format(profile.license_plate_state, profile.license_plate_number),
            profile.social_security_number,
            profile.date_of_birth,
        ])
        profile.exported_at = datetime.now().isoformat()
        profile.save()

    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response

@login_required(login_url='/lots-login/')
def csv_dump(request, pilot, status, content='application'):
    if content == 'application':
        response = dump_applications(request, pilot, status)

    elif content == 'ppf':
        response = dump_principal_profiles(request, pilot)

    return response

@login_required(login_url='/lots-login/')
def delete_principal_profiles(request, pilot):
    # Admins should not be given the option to delete Principal Profile
    # forms until all of them have been exported. All the same, protectively
    # filter out profiles without an exported_at date to avoid accidental
    # information loss (however improbable it may be).
    principal_profiles = PrincipalProfile.objects\
                                         .filter(application__pilot=pilot)\
                                         .filter(deleted_at__isnull=True)\
                                         .filter(exported_at__isnull=False)

    n_deleted = len(principal_profiles)

    for ppf in principal_profiles:

        for field in ('date_of_birth',
                      'social_security_number',
                      'drivers_license_state',
                      'drivers_license_number',
                      'license_plate_state',
                      'license_plate_number'):

            setattr(ppf, field, None)

        ppf.deleted_at = datetime.now().isoformat()
        ppf.save()

    return HttpResponseRedirect('/principal-profiles/')

@login_required(login_url='/lots-login/')
def pdfviewer(request):
    return render(request, 'pdfviewer.html')

@login_required(login_url='/lots-login/')
def deny_application(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    warning = None
    notice = None

    # Prevent LargeLots admin from re-evaluating the same application.
    # Check if application has been denied with a current step of None.
    if application_status.current_step is None and application_status.denied:
        warning = True

    # Determine if another applicant advances to Step 5, as a result of this denial.
    try:
        competing_application_status = ApplicationStatus.objects.exclude(id=application_status.id).get(lot=application_status.lot.pin, denied=False)
    except (MultipleObjectsReturned, ApplicationStatus.DoesNotExist):
        competing_application_status = None
    else:
        if competing_application_status.current_step.step != 4:
            competing_application_status = None

    return render(request, 'deny_application.html', {
        'application_status': application_status,
        'denial_reason': DENIAL_REASONS[request.GET.get('reason')],
        'warning': warning,
        'competing_application_status': competing_application_status
        })

@login_required(login_url='/lots-login/')
def deny_submit(request, application_id):
    # Retrieve application
    application_status = ApplicationStatus.objects.get(id=application_id)
    application_status.denied = True
    application_status.current_step = None
    application_status.save()

    # Create review
    reason, _ = DenialReason.objects.get_or_create(value=request.POST.get('reason'))
    Review.objects.create(reviewer=request.user, email_sent=True, denial_reason=reason, application=application_status, step_completed=2)

    try:
        send_denial_email(request, application_status)
    except SMTPException as stmp_e:
        request.session['email_error_app_ids'] = [application_status.id]
        return HttpResponseRedirect(reverse('email_error'))

    '''
    Multiple applicants (including the one denied here) may have requested this lot.
    After this denial, the following may be true:
    (1) One valid applicant for this lot remains;
    (2) The remaining applicant is on Step 4.
    If so, advance that applicant to Step 5.
    '''
    try:
        last_application_status = ApplicationStatus.objects.get(lot=application_status.lot.pin, denied=False)
    except (MultipleObjectsReturned, ApplicationStatus.DoesNotExist):
        pass
    else:
        if last_application_status.current_step.step == 4:
            advance_to_step('letter', last_application_status)
            Review.objects.create(reviewer=request.user, email_sent=False, application=last_application_status, step_completed=4)

    redirect_path = create_redirect_path(request)

    return HttpResponseRedirect('/lots-admin/all/%s' % redirect_path )


@login_required(login_url='/lots-login/')
def double_submit(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)

    return render(request, 'double_submit.html', {
        'application_status': application_status,
        })

@login_required(login_url='/lots-login/')
def deed_check(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    warning = None

    # Check if application has been denied and has a current step of None.
    if application_status.current_step is None and application_status.denied:
        warning = 'Denied'
    # If not, then check if application has step different than the view.
    elif application_status.current_step.step != 2:
        warning = 'Reviewed'

    return render(request, 'deed_check.html', {
        'application_status': application_status,
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

        '''
        The first two conditions prevent a LargeLots admin from re-evaluating an application that:
        (1) has already been denied;
        (2) advanced past Step 2. 
        '''
        if application_status.current_step == None:
            return HttpResponseRedirect('/double-submit/%s/' % application_status.id)
        elif application_status.current_step.step != 2:
            return HttpResponseRedirect('/double-submit/%s/' % application_status.id)
        # Move to step 3 of review process.
        elif (name == 'on' and address == 'on' and church == 'no' and document == 'yes'):
            step, _ = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['location'], public_status='valid', step=3)
            application_status.current_step = step
            application_status.save()

            review = Review(reviewer=user, email_sent=False, application=application_status, step_completed=2)
            review.save()

            return HttpResponseRedirect('/application-review/step-3/%s/' % application_status.id)
        # Send admin to denial confirmation page.
        else:
            if (document == 'no'):
                reason = 'document'
            elif (church == 'yes'):
                reason = 'church'
            elif (name == 'off' and address == 'on'):
                reason = 'name'
            elif (name == 'on' and address == 'off'):
                reason = 'address'
            else:
                reason = 'nameaddress'

            return HttpResponseRedirect('/deny-application/{app_id}/?reason={reason}'.format(app_id=application_status.id, reason=reason))

@login_required(login_url='/lots-login/')
def deed_duplicate_submit(request, application_id):
    if request.method == 'POST':
        application_status = ApplicationStatus.objects.get(id=application_id)
        user = request.user

        reason, _ = DenialReason.objects.get_or_create(value=DENIAL_REASONS['deedoveruse'])
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

        reason, _ = DenialReason.objects.get_or_create(value=DENIAL_REASONS['duplicate'])
        review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=application_status, step_completed=2)
        review.save()

        application_status.denied = True
        application_status.save()

        return HttpResponseRedirect('/deny-application/%s/' % application_status.id)

@login_required(login_url='/lots-login/')
def location_check(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    warning = None

    # Check if application has been denied and has a current step of None.
    if application_status.current_step is None and application_status.denied:
        warning = 'Denied'
    # If not, then check if application has step different than the view.
    elif application_status.current_step.step != 3:
        warning = 'Reviewed'

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
        'boundaries': settings.CURRENT_BOUNDARIES,
        'cartodb_table': settings.CURRENT_CARTODB,
    })

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
        redirect_path = create_redirect_path(request)

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
                step, _ = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['multi'], public_status='valid', step=4)
                application_status.current_step = step
                application_status.save()

                return HttpResponseRedirect('/lots-admin/all/%s' % redirect_path )
            else:
                # Move to Step 5: Adlerman letter.
                step, _ = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='valid', step=5)
                application_status.current_step = step
                application_status.save()

                return HttpResponseRedirect('/lots-admin/all/%s' % redirect_path )
        # Send admin to denial confirmation page.
        else:
            reason = 'block'

            return HttpResponseRedirect('/deny-application/{app_id}/?reason={reason}'.format(app_id=application_status.id, reason=reason))

@login_required(login_url='/lots-login/')
def multiple_applicant_check(request, application_id):
    warning = None
    application_status = ApplicationStatus.objects.get(id=application_id)

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
        'other_owned_pins': json.dumps(other_owned_pins),
        'warning': warning,
        'boundaries': settings.CURRENT_BOUNDARIES,
        'cartodb_table': settings.CURRENT_CARTODB,
    })

@login_required(login_url='/lots-login/')
def multiple_location_check_submit(request, application_id):
    if request.method == 'POST':
        user = request.user
        applications = request.POST.getlist('multi-check')
        application_ids = [int(i) for i in applications]
        applications = ApplicationStatus.objects.filter(id__in=application_ids)

        # Did the admin check multiple applicants? If so, tag them with lottery boolean.
        if (len(applications) > 1):
            for a in applications:
                a.lottery = True
                a.save()

        # Applicant(s) with a check should advance to step 5.
        for a in applications:
            step, _ = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['letter'], public_status='valid', step=5)
            a.current_step = step
            a.save()
            review = Review(reviewer=user, email_sent=False, application=a, step_completed=4)
            review.save()

        # Deny unchecked applications, and send them emails.
        application_status = ApplicationStatus.objects.get(id=application_id)
        lot_pin = application_status.lot.pin
        applicants_to_deny = ApplicationStatus.objects.filter(lot=lot_pin, denied=False).exclude(id__in=application_ids)
        email_error_app_ids = []

        for a in applicants_to_deny:
            reason, _ = DenialReason.objects.get_or_create(value=DENIAL_REASONS['adjacent'])
            review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=a, step_completed=4)
            review.save()
            a.denied = True
            a.current_step = None
            a.save()

            try:
                send_denial_email(request, a)
            except SMTPException as stmp_e:
                email_error_app_ids.append(a.id)
        # If any emails raised an error, redirect to the email-error page.
        if email_error_app_ids:
            request.session['email_error_app_ids'] = email_error_app_ids
            return HttpResponseRedirect(reverse('email_error'))

        redirect_path = create_redirect_path(request)

        return HttpResponseRedirect('/lots-admin/all/%s' % redirect_path )

@login_required(login_url='/lots-login/')
def lotteries(request):
    # Get all applications that will go to lottery.
    applications = ApplicationStatus.objects.filter(current_step__step=6).filter(lottery=True).order_by('application__last_name')
    applications_list = list(applications)
    # Get all lots.
    lots = set()
    for a in applications_list:
        lots.add(a.lot)
    # # Deduplicate applied_pins array.
    # lots_list = list(set(lots))
    lots_list = sorted(lots, key=lambda lot: lot.pin)

    return render(request, 'lotteries.html', {
        'lots_list': lots_list,
        })

@login_required(login_url='/lots-login/')
def lottery(request, lot_pin):
    lot = Lot.objects.get(pin=lot_pin)

    applications = ApplicationStatus.objects.filter(current_step__step=6).filter(lottery=True).filter(lot=lot_pin).order_by('application__last_name')
    applications_list = list(applications)

    return render(request, 'lottery.html', {
        'applications': applications,
        'lot': lot,
        })

@login_required(login_url='/lots-login/')
def lottery_submit(request, lot_pin):
    if request.method == 'POST':
        user = request.user
        winner_id = int(request.POST['winner-select'])
        winning_app = ApplicationStatus.objects.get(id=winner_id)

        # Move lottery winner to Step 7.
        step, _ = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['EDS_waiting'], public_status='valid', step=7)
        winning_app.current_step = step
        winning_app.save()
        # Create a review.
        review = Review(reviewer=user, email_sent=True, application=winning_app, step_completed=6)
        review.save()
        # Send winner an email.
        context = {'app': winning_app.application, 
                   'lot': winning_app.lot}

        msg = create_email_msg(
            'lotto_winner_email', 
            'LargeLots application - Lottery winner', 
            winning_app.application.email, 
            context
        )

        email_error_app_ids = []

        try:
            msg.send()
            winning_app.lottery_email_sent = True
            winning_app.save()
        except SMTPException as stmp_e:
            email_error_app_ids.append(winning_app.id)

        # Deny lottery losers: find all applications on Step 5.
        losing_apps = ApplicationStatus.objects.filter(current_step__step=6).filter(lot=lot_pin)
        for a in losing_apps:
            # Deny each application.
            reason, _ = DenialReason.objects.get_or_create(value=DENIAL_REASONS['lottery'])
            review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=a, step_completed=6)
            review.save()
            a.denied = True
            a.current_step = None
            a.save()

            # Send loser an email.
            context = {'app': a.application, 
                       'lot': a.lot,
                       'review': review,
                       'today': datetime.now().date(),
                       'DENIAL_REASONS': DENIAL_REASONS
                       }

            msg = create_email_msg(
                'denial_email', 
                'LargeLots application - Lottery results', 
                a.application.email, 
                context
            )

            try:
                msg.send()
                a.lottery_email_sent = True
                a.save()
            except SMTPException as stmp_e:
                email_error_app_ids.append(a)

        if email_error_app_ids:
            request.session['email_error_app_ids'] = email_error_app_ids
            return HttpResponseRedirect(reverse('email_error'))

        return HttpResponseRedirect(reverse('lotteries'))

@login_required(login_url='/lots-login/')
def review_EDS(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)
    return render(request, 'review_EDS.html', {
        'application_status': application_status
        })

@login_required(login_url='/lots-login/')
def review_status_log(request, application_id):
    '''
    This view contains a form that allows LargeLots admins to update the owned_pin and related address 
    of an application. The admin can update the pin, address, or both. 
    
    If the admin submits a valid form with changes, then this view creates an UpdatedEntity, 
    which keeps track of such updates made by admins. 
    '''
    application_status = ApplicationStatus.objects.get(id=application_id)
    reviews = Review.objects.filter(application=application_status)
    application = Application.objects.get(applicationstatus__id=application_id)

    future_list = [2, 3, 4, 5, 6, 7]
    
    application_form = ApplicationUpdateForm(instance=application)
    address_form = AddressUpdateForm(instance=application.owned_address)

    success = False 

    if request.method == 'POST':
        update_info = {'admin': request.user, 'application': application}
        application_form = ApplicationUpdateForm(request.POST, instance=application)
        address_form = AddressUpdateForm(request.POST, instance=application.owned_address)
        
        if application_form.is_valid() and address_form.is_valid():
            application_form.save()
            address_form.save()

            if 'owned_pin' in application_form.changed_data:
                update_info['owned_pin'] = application.owned_pin
            else:
                update_info['owned_pin'] = 'No changes'

            if 'street' in address_form.changed_data:
                update_info['street'] = application.owned_address
            else:
                update_info['street'] = 'No changes'
        
            UpdatedEntity.objects.create(**update_info)
            success = True

    return render(request, 'review_status_log.html', {
        'address_form': address_form,
        'application_form': application_form,
        'application_status': application_status,
        'reviews': reviews,
        'future_list': future_list,
        'success': success,
        })

@login_required(login_url='/lots-login/')
def bulk_submit(request):
    if request.method == 'POST':
        selected_step, = request.POST.getlist('step')
        selected_apps = request.POST.getlist('selected-for-bulk-submit')
        selected_app_ids = [int(i) for i in selected_apps]

        if selected_step == 'deny':
            # Save application ids in session, and redirect to bulk deny view.
            request.session['application_ids'] = selected_app_ids
            return HttpResponseRedirect('/bulk-deny')

        else:
            user = request.user
            application_statuses = ApplicationStatus.objects\
                                                    .filter(id__in=selected_app_ids)

            for app_status in application_statuses:
                review_blob = {
                    'reviewer': user,
                    'email_sent': False,
                    'application': app_status,
                }

                if selected_step == 'step5':
                    # Check whether applicant goes to lottery.
                    if app_status.lottery:
                        advance_to_step('lottery', app_status)
                    else:
                        advance_to_step('EDS_waiting', app_status)

                    review_blob['step_completed'] = 5

                # Note: moving from step 7 (EDS_waiting) to step 8 (EDS_submission)
                # happens automatically, except when the applicant submits an EDS
                # through the City's system rather than our own.
                elif selected_step == 'step7':
                    app = app_status.application
                    app.eds_received = True
                    app.save()

                    advance_to_step('EDS_submission', app_status)
                    review_blob['step_completed'] = 7

                # In contrast to steps 2-7, the following steps confirm "past"
                # actions, i.e., an applicant on Step 10 has been certified
                # as free of debt and has thus "completed" that step.
                # Admins should use the email sending interface to move applicants from Step 8 to Step 9.
                elif selected_step == 'step10':
                    advance_to_step('debts', app_status)
                    review_blob['step_completed'] = 10

                elif selected_step == 'step11':
                    advance_to_step('sold', app_status)
                    review_blob['step_completed'] = 11

                else:  # Some invalid step was selected. Back to start!
                    return HttpResponseRedirect(reverse('lots_admin', args=['all']))

                Review.objects.create(**review_blob)

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
    email_error_app_ids = []

    for a in apps_to_deny:
        dict_reason = dictionary[a.id]
        reason, _ = DenialReason.objects.get_or_create(value=DENIAL_REASONS[dict_reason])

        review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=a)
        review.save()
        a.denied = True
        a.current_step = None
        a.save()

        try:
            send_denial_email(request, a)
        except SMTPException as stmp_e:
            email_error_app_ids.append(a.id)
    # If any emails raised an error, redirect to the email-error page.
    if email_error_app_ids:
        request.session['email_error_app_ids'] = email_error_app_ids
        return HttpResponseRedirect(reverse('email_error'))

    return HttpResponseRedirect(reverse('lots_admin', args=['all']))

@login_required(login_url='/lots-login/')
def status_tally(request):
    total = ApplicationStatus.objects.all()

    step2 = ApplicationStatus.objects.filter(current_step__step=2)
    step3 = ApplicationStatus.objects.filter(current_step__step=3)
    step4 = ApplicationStatus.objects.filter(current_step__step=4)
    step5 = ApplicationStatus.objects.filter(current_step__step=5)
    step6 = ApplicationStatus.objects.filter(current_step__step=6)
    step7 = ApplicationStatus.objects.filter(current_step__step=7)
    step8 = ApplicationStatus.objects.filter(current_step__step=8)
    step9 = ApplicationStatus.objects.filter(current_step__step=9)
    step10 = ApplicationStatus.objects.filter(current_step__step=10)
    sold = ApplicationStatus.objects.filter(current_step__step=11)
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
        'sold': sold,
        'denied': denied
        })

def advance_to_step(description_key, app_status):
    spec = {
        'description': APPLICATION_STATUS[description_key],
        'public_status': 'valid',
        'step': step_from_status(description_key),
    }

    step, _ = ApplicationStep.objects.get_or_create(**spec)

    app_status.current_step = step
    app_status.save()

@login_required(login_url='/lots-login/')
def deed(request, application_id):
    application_status = ApplicationStatus.objects.get(id=application_id)

    return render(request, 'deed.html', {
        'application_status': application_status,
        })

@login_required(login_url='/lots-login/')
def email_error(request):
    email_error_app_ids = request.session['email_error_app_ids']

    applicant_statuses = ApplicationStatus.objects.filter(id__in=email_error_app_ids)

    return render(request, 'email_error.html', {
        'applicant_statuses': applicant_statuses,
    })

@login_required(login_url='/lots-login/')
def send_emails_notice(request):
    failures = request.session['failures']

    app_ids = [val.split('|')[0] for val in failures]
    errors = [val.split('|')[1] for val in failures]
    applications = Application.objects.filter(id__in=app_ids)

    if applications:
        failure_log = zip(applications, errors)
    else: 
        failure_log = None

    return render(request, 'send_emails_notice.html', {
        'failure_log': failure_log,
    })


from django.contrib.auth.mixins import LoginRequiredMixin

class EmailHandler(LoginRequiredMixin, TemplateView):
    login_url = '/lots-login/'
    template_name = 'send_emails.html'
    form_map = {
        'eds_form': EdsEmailForm, 
        'final_eds_form': FinalEdsEmailForm,
        'eds_denial_form': EdsDenialEmailForm,
        'lottery_form': LotteryEmailForm,
        'closing_time_form': ClosingTimeEmail,
        'custom_form': CustomEmail,
    }
    success_url = '/send-emails-notice/'

    def _get_form_class(self):
        action = self.request.POST['action']
        return self.form_map[action]

    def get_context_data(self, **kwargs):
        self.request.session['failures'] = None
        
        context = super().get_context_data(**kwargs)
        
        lottery_count = Lot.objects.filter(applicationstatus__current_step__step=6).distinct().count()
        context['lottery_count'] = lottery_count
        context.update(**self.form_map)

        if self.request.POST.get('action'):
            action = self.request.POST.get('action')
            context[action] = kwargs['form']

        return context 

    def post(self, request, *args, **kwargs):
        form_class = self._get_form_class()
        form = form_class(request.POST)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def form_valid(self, form):
        out = StringIO()
        base_context = {}
        
        if self.request.POST.get('action') == 'custom_form':
            form.step = form.cleaned_data['step']
            form.selection = form.cleaned_data['selection']
            form.every_status = form.cleaned_data['every_status']
            base_context['subject'] = form.cleaned_data['subject']
            base_context['email_text'] = form.cleaned_data['email_text']

        base_context['time'] = form.cleaned_data.get('time')
        base_context['date'] = form.cleaned_data.get('date')
        base_context['location'] = form.cleaned_data.get('location')
        form.base_context = base_context
        form.user = self.request.user
        form.out = out

        if 'number' in form.cleaned_data:
            form.number = form.cleaned_data['number']

        form._call_command()
        
        failures_list = form.out.getvalue().splitlines()
        self.request.session['failures'] = failures_list

        return HttpResponseRedirect('/send-emails-notice/')
