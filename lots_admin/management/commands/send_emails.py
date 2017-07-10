from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings

from smtplib import SMTPException
import time
from datetime import datetime

from lots_admin.models import Application, ApplicationStatus, Review, DenialReason, User
from lots_admin.look_ups import DENIAL_REASONS

class Command(BaseCommand):
    help = 'Send emails to applicants who need to resubmit deeds'


    def add_arguments(self, parser):
        parser.add_argument('--eds_email',
                            action='store_true',
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
        if options['eds_email']:
            application_status_objs = ApplicationStatus.objects.all()

            print("Emails sent to:")
            for app in application_status_objs:
                if app.current_step:
                    if app.current_step.step == 7 and app.application.eds_sent != True:
                        # Send email
                        context = {
                            'app': app.application,
                        }
                        self.send_email('eds_email', 'LargeLots application - Economic Disclosure Statement (EDS)', app.application.email, context)
                        print(app.application.first_name, app.application.last_name, " - Application ID", app.application.id)

                        # Find other applications and change status
                        related_applications = Application.objects.filter(email=app.application.email).filter(applicationstatus__current_step__step=7)
                        print("Apps with the same email: ", related_applications)
                        for application in related_applications:
                            application.eds_sent = True
                            application.save()


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



