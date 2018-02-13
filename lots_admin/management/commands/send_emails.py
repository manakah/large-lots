from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings
from django.db import connection

from smtplib import SMTPException
import time
from datetime import datetime

from lots_admin.models import Application, ApplicationStatus, ApplicationStep, Review, DenialReason, User, Lot
from lots_admin.look_ups import DENIAL_REASONS

class Command(BaseCommand):
    help = 'Send bulk emails to Large Lots applicants. By default, all applications ' + \
        'associated with an email address will be aggregated, and one email will ' + \
        'be sent. See --separate_emails for handling shared email addresses.'


    def add_arguments(self, parser):
        parser.add_argument('--eds_denial',
                            action='store_true',
                            help='Send denial emails to applicants who did not submit EDS')

        parser.add_argument('--separate_emails',
                            help='Comma-separated list of email addresses. ' + \
                                'In contrast to the default behavior of one aggregate ' + \
                                'email, separate emails will be sent for each ' + \
                                'application associated with the provided email ' + \
                                'addresses. This is useful when one email address ' + \
                                'is in use by more than one applicant.')

        parser.add_argument('--closing_invitations',
                            help='Send closing invitations to applicants')

        parser.add_argument('--date',
                            help='Date in format YYYY-MM-DD for emails, etc.')

        parser.add_argument('--closing_time',
                            action='store_true',
                            help='Send closing notifications to applicants')

        parser.add_argument('--city_council_denial',
                            action='store_true',
                            help='Send denial emails to applicants denied by City Council')

        parser.add_argument('--eds_final_email',
                            action='store_true',
                            help='Send email to all applicants on Step 7.')

        parser.add_argument('--lotto_email',
                            help='Send email with notification of lottery. Use one of two arguments: morning or afternoon.')

        parser.add_argument('--lotto_offset',
                            help='Set SQL offset.')

        parser.add_argument('--eds_email',
                            help='Send email with link to complete EDS')

        parser.add_argument('--deed_upload',
                            action='store_true',
                            help='Send emails to applicants who need to resubmit a deed')

        parser.add_argument('--humboldt_denial',
                            action='store_true',
                            help='Send denial emails to applicants in Homboldt Park and Ward 27')

        parser.add_argument('--garfield_denial',
                            action='store_true',
                            help='Send denial emails to applicants in Garfield and Ward 27')

        parser.add_argument('--blank_deed_denial',
                            action='store_true',
                            help='Send denial emails to applicants who did not resubmit blank deeds')

        parser.add_argument('--update_email',
                            action='store_true',
                            help='Send emails to insure applicants that "everything is okay"')

        parser.add_argument('--wintrust_email',
                            action='store_true',
                            help='Send emails about a special event')


    def handle(self, *args, **options):
        if options['eds_denial']:

            if options['separate_emails']:
                separate_emails = options['separate_emails'].split(',')
            else:
                separate_emails = []

            # Get email and application IDs where there are active applications
            # on step 7.
            query = '''
                SELECT
                  email,
                  ARRAY_AGG(DISTINCT app.id)
                FROM lots_admin_application AS app
                JOIN lots_admin_applicationstatus AS status
                ON app.id = status.application_id
                JOIN lots_admin_applicationstep AS step
                ON status.current_step_id = step.id
                WHERE denied = False
                AND step = 7
                GROUP BY email
            '''

            with connection.cursor() as cursor:
                cursor.execute(query)
                applicants = [(email, app_ids) for email, app_ids in cursor]

            log_fmt = '{date} {applicant} ({email}) denied due to ' + \
                    'lack of EDS for lots #{pins}'

            # Set up denial globals
            no_eds, _ = DenialReason.objects.get_or_create(value=DENIAL_REASONS['EDS'])
            admin_user = User.objects.get(id=5)

            # Define some reusable functionality.

            def step_7_lots_list(application_obj):
                '''Return list of lots for given applicant for which there
                is an active application on step 7.
                '''
                return list(application_obj.lot_set\
                                           .filter(application__applicationstatus__current_step_id__step=7)\
                                           .filter(application__applicationstatus__denied=False)\
                                           .distinct())

            def assemble_and_send_email(application, lots):
                '''Assemble email context and send email.'''
                context = {
                    'app': application,
                    'lots': lots
                }

                self.send_email(
                    'eds_denial_email',
                    'LargeLots application - Denial',
                    application.email,
                    context
                )

            def log(application, lots):
                print(log_fmt.format(
                    date=datetime.now().strftime('%Y-%m-%d %H:%M'),
                    applicant=' '.join([application.first_name, application.last_name]),
                    email=application.email,
                    phone=application.phone,
                    pins=', #'.join(str(lot.pin) for lot in lots)
                ))

            for email, app_ids in applicants:
                # Get application objects where the applicant is on step 7.
                # (Some applicants have more than one application.)
                applications = Application.objects.filter(id__in=list(app_ids))

                if email in separate_emails:
                    # In the case of a shared email address, send denial
                    # emails for each individual application.
                    for application in applications:
                        lots = step_7_lots_list(application)

                        for app_status in application.applicationstatus_set\
                                                     .filter(current_step_id__step=7):

                            self.deny(app_status, no_eds, admin_user)

                        assemble_and_send_email(application, lots)

                        log(application, lots)

                else:
                    # Aggregate information from applications and send one email.
                    lots = []

                    for app in applications:
                        lots += step_7_lots_list(app)

                        for app_status in app.applicationstatus_set\
                                             .filter(current_step_id__step=7):

                            self.deny(app_status, no_eds, admin_user)

                    application = applications.first()

                    assemble_and_send_email(application, lots)

                    log(application, lots)

        if options['closing_invitations']:
            n = int(options['closing_invitations'])
            date = datetime.strptime(options['date'], '%Y-%m-%d')

            with connection.cursor() as cursor:
                query = '''
                    SELECT
                      email,
                      ARRAY_AGG(lot_id) AS pins,
                      ARRAY_AGG(id) AS status_ids
                    FROM (
                      SELECT
                        email,
                        status.lot_id,
                        status.id
                      FROM lots_admin_application AS app
                      JOIN lots_admin_applicationstatus AS status
                      ON app.id = status.application_id
                      JOIN lots_admin_applicationstep AS step
                      ON status.current_step_id = step.id
                      WHERE step = 10
                        AND closing_invite_sent = False
                      ORDER BY last_name, first_name
                    ) AS applicants
                    GROUP BY email
                    LIMIT {n}
                '''.format(n=n)

                cursor.execute(query)

                applicant_list = [(email, pins, status_ids) for email, pins, status_ids in cursor]

                date_fmt = '%Y-%m-%d %H:%M'

                log_fmt = '{date} {applicant} ({email}, {phone}) invited to ' + \
                    'Closing {event} for lots #{pins}'

                for idx, applicant in enumerate(applicant_list, start=1):
                    email, pins, status_ids = applicant

                    # Status ID filter prevents us from grabbing an Application
                    # with a shared email address that does _not_ belong to the
                    # applicant we mean to notify

                    applications = Application.objects\
                                              .filter(email=email)\
                                              .filter(applicationstatus__id__in=status_ids)

                    application = applications.first()

                    lots = [Lot.objects.get(pin=pin) for pin in pins]

                    date_parts = [getattr(date, k) for k in ('year', 'month', 'day')]

                    # Invite half the applicants to the morning event, and
                    # half to the afternoon event, using len of applicant list
                    # rather than initial n to handle case where we get fewer
                    # than n applicants

                    if idx <= len(applicant_list) / 2:
                        date_parts += [9, 0]
                        event = datetime(*date_parts)
                    else:
                        date_parts += [13, 0]
                        event = datetime(*date_parts)

                    context = {
                        'app': application,
                        'lots': lots,
                        'event': event,
                    }

                    self.send_email(
                        'closing_invitation_email',
                        'Large Lot Closing Date and Time',
                        email,
                        context,
                    )

                    # Update all because we only want to send one invitation
                    # per applicant (who may have multiple applications)

                    for app in applications:
                        app.closing_invite_sent = True
                        app.save()

                    print(log_fmt.format(
                        date=datetime.now().strftime(date_fmt),
                        applicant=' '.join([application.first_name, application.last_name]),
                        email=application.email,
                        phone=application.phone,
                        event=event.strftime(date_fmt),
                        pins=', #'.join(str(pin) for pin in pins),
                    ))

        if options['closing_time']:
            with connection.cursor() as cursor:
                query = '''
                    SELECT email, array_agg(status.lot_id) AS pins, array_agg(status.id) AS status_ids
                    FROM lots_admin_application AS app
                    JOIN lots_admin_applicationstatus AS status
                    ON status.application_id = app.id
                    JOIN lots_admin_applicationstep AS step
                    ON status.current_step_id = step.id 
                    WHERE denied = False and step = 8
                    GROUP BY email
                '''

                cursor.execute(query)

                applicant_list = [(email, pins, status_ids) for email, pins, status_ids in cursor]

                print("Emails sent to:")
                for email, pins, status_ids in applicant_list:
                    # Isolate one applicant - to pass into "context"
                    application = Application.objects.filter(email=email).filter(applicationstatus__id__in=status_ids).first()

                    lots = [Lot.objects.get(pin=pin) for pin in pins]
                    
                    context = {
                        'app': application,
                        'lots': lots
                    }

                    self.send_email(
                        'closing_time_email', 
                        'Closing Time for Large Lots', 
                        email, 
                        context
                    )

                    # Move applicants to Step 9
                    application_statuses = ApplicationStatus.objects.filter(id__in=status_ids)
                    step9 = ApplicationStep.objects.get(step=9)
                    for a in application_statuses:
                        a.current_step = step9
                        a.save()

                    print('{0} - Lots: {1}'.format(email, pins))


        if options['city_council_denial']:
            application_statuses = ApplicationStatus.objects.filter(lot_id__in=['25223200170000','25223200190000','20211210110000','20211120350000','20211210030000','20211130370000','20211130160000','20211120060000','20211110160000','20211130040000','20211130180000','20211120380000','20082150270000','20032190350000','20032230250000','20032230270000','20032230380000','20032240510000','25291050490000','20034050130000']).filter(denied=False)

            print("Emails sent to:")
            for app in application_statuses:             
                context = {
                    'app': app.application,
                    'lot': app.lot
                }
                
                applicant = self.applicant_detail_str(app.application)
                print('Notified {}'.format(applicant))

                self.send_email(
                    'city_council_denial_email', 
                    'LargeLots application - Denial', 
                    app.application.email, 
                    context
                )

        if options['eds_final_email']:
            # Send final notice email to all applicants on Step 7.
            with connection.cursor() as cursor:
                query = '''
                    SELECT
                      MIN(id) as id,
                      email
                    FROM (
                      SELECT
                        app.id,
                        email,
                        step,
                        denied
                      FROM lots_admin_application AS app
                      JOIN lots_admin_applicationstatus AS status
                      ON app.id = status.application_id
                      JOIN lots_admin_applicationstep AS step
                      ON status.current_step_id = step.id
                      WHERE denied = False
                      AND step = 7
                    ) AS applicants
                    GROUP BY email 
                '''

                cursor.execute(query)

                applicants = [(app_id, email_address) for app_id, email_address in cursor]

            for app_id, email_address in applicants:
                
                application = Application.objects.filter(id=app_id).first()               
                context = {'app': application}
                self.send_email(
                    'eds_email', 
                    'LargeLots application - Economic Disclosure Statement (EDS)', 
                    email_address, 
                    context
                )

                applicant = self.applicant_detail_str(application)
                print('Notified {}'.format(applicant))


        if options['lotto_email']:
            time = options['lotto_email']
            offset = int(options['lotto_offset']) - 1

            if time == 'morning':
                comparator = '<='
            if time == 'afternoon':
                comparator = '>' 

            # This query grabs the lot pin, which lies at a specified mid-way point, e.g.,
            # if we want to notify the applicants who applied to the first 85 lots (in ascending order),
            # then the offset will be 84.  
            with connection.cursor() as cursor:
                query = '''
                    SELECT DISTINCT lot_id
                    FROM lots_admin_applicationstatus as status
                    JOIN lots_admin_applicationstep as step
                    ON status.current_step_id=step.id
                    WHERE step=6
                    ORDER BY lot_id
                    LIMIT 1 OFFSET {offset}
                '''.format(offset=offset)

                cursor.execute(query)
                lot_id = cursor.fetchone()[0]

            with connection.cursor() as cursor:
                query = '''
                    SELECT status.id, status.lot_id, email 
                    FROM lots_admin_applicationstatus as status
                    JOIN lots_admin_applicationstep as step
                    ON status.current_step_id=step.id
                    JOIN lots_admin_application as app
                    ON app.id=status.application_id
                    WHERE step=6
                    AND status.lottery_email_sent = False
                    AND status.lot_id {comparator} '{lot_id}'
                    ORDER BY status.lot_id
                '''.format(comparator=comparator, lot_id=lot_id)

                cursor.execute(query)
                applicants = [(status_id, lot_id, email_address) for status_id, lot_id, email_address in cursor]

            for status_id, lot_id, email_address in applicants:
                status = ApplicationStatus.objects.get(id=status_id)
                application = Application.objects.get(id=status.application_id)
                lot = Lot.objects.get(pin=lot_id)              
                context = {'app': application, 
                           'lot': lot}
                self.send_email(
                    'lottery_notification_{}'.format(time), 
                    'LargeLots application - Lottery', 
                    email_address, 
                    context
                )

                status.lottery_email_sent = True
                status.save()

                applicant = self.applicant_detail_str(application)
                print('Notified {}'.format(applicant))


        if options['eds_email']:
            limit = options['eds_email']

            # Select only applicants whose non-denied applications
            # are all on step 7 in order to avoid a situation where
            # an applicant has active applications at other steps,
            # as these will get stuck if the applicant submits an
            # EDS prior to their reaching step 7. (The applicant
            # will not submit another EDS, thus the endpoint to 
            # advance the remaining applications will never be
            # pinged.)

            with connection.cursor() as cursor:
                query = '''
                    SELECT
                      MIN(id) as id,
                      email
                    FROM (
                      SELECT
                        app.id,
                        email,
                        step,
                        denied
                      FROM lots_admin_application AS app
                      JOIN lots_admin_applicationstatus AS status
                      ON app.id = status.application_id
                      JOIN lots_admin_applicationstep AS step
                      ON status.current_step_id = step.id
                      WHERE eds_sent = False 
                        AND denied = False
                    ) AS applicants
                    GROUP BY email 
                    HAVING (EVERY(step = 7))
                    LIMIT {limit}
                '''.format(limit=limit)

                cursor.execute(query)

                applicants = [(app_id, email_address) for app_id, email_address in cursor]

            for app_id, email_address in applicants:
                
                application = Application.objects.filter(id=app_id).first()               
                context = {'app': application}
                self.send_email(
                    'eds_email', 
                    'LargeLots application - Economic Disclosure Statement (EDS)', 
                    email_address, 
                    context
                )

                applicant = self.applicant_detail_str(application)
                print('Notified {}'.format(applicant))

                # Set `eds_sent` = True on all applications for given applicant
                # (since we only need one EDS per applicant)
                active_applications = ApplicationStatus.objects\
                                                       .filter(application__email=email_address)\
                                                       .filter(denied=False)

                print('Updated applications for {}:'.format(applicant))
                for app in active_applications:
                    print(self.applicant_detail_str(app.application))
                    app.application.eds_sent = True
                    app.application.save()
                    

        if options['deed_upload']:
            applications = Application.objects.all()

            print("Emails sent to:")
            for application in applications:
                application_status_objs = ApplicationStatus.objects.filter(application_id=application.id)
                wards = []
                for status in application_status_objs:
                    wards.append(status.lot.address.ward)

                try:
                    first_ward = wards[0]
                except:
                    first_ward = ''

                try:
                    second_ward = wards[1]
                except:
                    second_ward = ''

                if application.deed_image == '':
                    print(application.first_name, application.last_name, " - Application ID", application.id)
                    print('Wards:', wards)

                    context = {
                        'app': application,
                        'lots': application.lot_set.all()
                    }

                    self.send_email('deed_inquiry_email', 'Important notice from Large Lots', application.email, context)

        if options['humboldt_denial']:
            application_statuses = ApplicationStatus.objects.all()

            print("Emails sent to:")
            for app in application_statuses:
                if app.current_step:
                    if app.current_step.step != 7 and app.denied == False and app.lot.address.ward == '27' and app.lot.address.community == 'HUMBOLDT PARK':
                        print(app.application.first_name, app.application.last_name, " - Application ID", app.application.id, " - Status", app.id)
                        print(datetime.now())

                        context = {
                            'app': app.application,
                            'lot': app.lot
                        }

                        self.send_email('denial_humboldt_email', 'Large Lots Application', app.application.email, context)

        if options['garfield_denial']:
            application_statuses = ApplicationStatus.objects.all()

            print("Emails sent to:")
            for app in application_statuses:
                if app.current_step:
                    if app.current_step.step != 7:
                        print(app.application.first_name, app.application.last_name, " - Application ID", app.application.id, " - Status", app.id)
                        print(datetime.now())

                        context = {
                            'app': app.application,
                            'lot': app.lot
                        }

                        self.send_email('denial_garfield_email', 'Large Lots Application', app.application.email, context)

        if options['blank_deed_denial']:
            application_statuses = ApplicationStatus.objects.all()

            print("Emails sent to:")
            for app in application_statuses:
                if app.current_step:
                    if app.current_step.step == 2 and app.denied == False and app.application.deed_image == '':
                        print(app.application.first_name, app.application.last_name, " - Application ID", app.application.id, " - Status", app.id)
                        print(datetime.now())

                        user = User.objects.get(id=5)
                        reason, created = DenialReason.objects.get_or_create(value=DENIAL_REASONS['document'])
                        review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=application_status, step_completed=2)
                        review.save()

                        context = {
                            'app': application_status.application,
                            'lot': application_status.lot,
                            'review': review,
                            'DENIAL_REASONS': DENIAL_REASONS,
                        }

                        self.send_email('emails/deny_html_email', 'Large Lots Application', application_status.application.email, context)

        if options['update_email']:
            application_statuses = ApplicationStatus.objects.all()

            print("Emails sent to:")
            for app in application_statuses:
                if app.id in [710, 1156, 1171, 1996, 2274, 2567, 2893, 2912, 3198, 3591, 3734, 3208, 502]:
                    print(app.application.first_name, app.application.last_name, " - Application ID", app.application.id)
                    print(datetime.now())

                    context = {
                        'app': app.application,
                        'lot': app.lot
                    }

                    self.send_email('update_email', 'Important update from Large Lots', app.application.email, context)

        if options['wintrust_email']:
            application_statuses = ApplicationStatus.objects.all()

            print("Emails sent to:")
            for app in application_statuses:
                if app.current_step:
                    if app.current_step.step in [4, 6] and app.denied == False:

                        print(app.application.first_name, app.application.last_name, " - Application ID", app.application.id)
                        print(datetime.now())

                        context = {
                            'app': app.application,
                            'lot': app.lot
                        }

                        self.send_email('wintrust_email', 'Special event for Large Lots applicants', app.application.email, context)

    def applicant_detail_str(self, application):
        return "{0} {1} - Application ID {2}".format(application.first_name,
                                                     application.last_name,
                                                     application.id)


    def send_email(self, template_name, email_subject, email_to_address, context):
        html_template = get_template('{}.html'.format(template_name))
        txt_template = get_template('{}.txt'.format(template_name))

        html_content = html_template.render(context)
        txt_content = txt_template.render(context)

        msg = EmailMultiAlternatives(email_subject,
                                txt_content,
                                settings.EMAIL_HOST_USER,
                                [email_to_address])

        msg.attach_alternative(html_content, 'text/html')

        try:
            msg.send()
        except SMTPException as stmp_e:
            print(stmp_e)
            print("Not able to send email due to smtp exception.")
        except Exception as e:
            print(e)
            print("Not able to send email.")

        time.sleep(5)


    def deny(self, app_status, denial_reason, admin_user):
        '''Deny the given application and create a corresponding review
        object.

        :app_status - ApplicationStatus object
        :denial_reason - DenialReason object
        :admin_user - User object (usually, an admin)
        '''
        app_status.denied = True
        app_status.current_step = None
        app_status.save()

        review = Review(reviewer=admin_user,
                        denial_reason=denial_reason,
                        application=app_status,
                        email_sent=True)

        review.save()



