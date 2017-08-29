from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings
from django.db import connection

from smtplib import SMTPException
import time
from datetime import datetime

from lots_admin.models import Application, ApplicationStatus, Review, DenialReason, User, Lot
from lots_admin.look_ups import DENIAL_REASONS

class Command(BaseCommand):
    help = 'Send bulk emails to Large Lots applicants'


    def add_arguments(self, parser):
        parser.add_argument('--lotto_winner_email',
                            action='store_true',
                            help='Send email to winners of the lottery.')

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
        if options['lotto_winner_email']:
            with connection.cursor() as cursor:
                query = '''
                    SELECT status.id, status.lot_id
                    FROM lots_admin_applicationstatus as status
                    JOIN lots_admin_applicationstep as step 
                    ON status.current_step_id=step.id 
                    WHERE step=7 and lottery=True
                '''

                cursor.execute(query)
                applicants = [(status_id, lot_id) for status_id, lot_id in cursor]

            for status_id, lot_id in applicants:
                status = ApplicationStatus.objects.get(id=status_id)
                application = Application.objects.get(id=status.application_id)
                lot = Lot.objects.get(pin=lot_id)              
                context = {'app': application, 
                           'lot': lot}
                self.send_email(
                    'lotto_winner_email', 
                    'LargeLots application - Lottery winner', 
                    application.email, 
                    context
                )

                status.lottery_email_sent = True
                status.save()

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

                        self.send_email('deny_html_email', 'Large Lots Application', application_status.application.email, context)

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



