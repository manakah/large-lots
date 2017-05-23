from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings

from smtplib import SMTPException
import time
from datetime import datetime

from lots_admin.models import Application, ApplicationStatus, Review

class Command(BaseCommand):
    help = 'Send emails to applicants who need to resubmit deeds'


    def add_arguments(self, parser):
        parser.add_argument('--deed_upload',
                            action='store_true',
                            help='Send emails to applicants who need to resubmit a deed')

        parser.add_argument('--update_email',
                            action='store_true',
                            help='Send emails to insure applicants that "everything is okay"')

        parser.add_argument('--wintrust_email',
                            action='store_true',
                            help='Send emails about a special event')

        parser.add_argument('--humbolt_denial',
                            action='store_true',
                            help='Send denial emails to applicants in Hombolt Park and Ward 27')

        parser.add_argument('--garfield_denial',
                            action='store_true',
                            help='Send denial emails to applicants in Garfield and Ward 27')


    def handle(self, *args, **options):
        if options['wintrust_email']:
            application_statuses = ApplicationStatus.objects.all()

            print("Emails sent to:")
            for app in application_statuses:
                if app.current_step:
                        if app.current_step.step in [4, 6] and app.denied == False and app.application.id > 2300:

                            print(app.application.first_name, app.application.last_name, " - Application ID", app.application.id)
                            print(datetime.now())

                            try:
                                self.send_wintrust_email(app)
                            except SMTPException as stmp_e:
                                print(stmp_e)
                                print("Not able to send email due to smtp exception.")
                            except Exception as e:
                                print(e)
                                print("Not able to send email.")

                            time.sleep(5)

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

                if application.deed_image == '' and application.id == 1574:
                    print(application.first_name, application.last_name, " - Application ID", application.id)
                    print('Wards:', wards)
                    try:
                        self.send_deed_email(application)
                    except SMTPException as stmp_e:
                        print(stmp_e)
                        print("Not able to send email due to smtp exception.")
                    except Exception as e:
                        print(e)
                        print("Not able to send email.")

                    time.sleep(2)

        if options['update_email']:
            application_statuses = ApplicationStatus.objects.all()

            print("Emails sent to:")
            for app in application_statuses:
                if app.id in [710, 1156, 1171, 1996, 2274, 2567, 2893, 2912, 3198, 3591, 3734, 3208, 502]:
                    print(app.application.first_name, app.application.last_name, " - Application ID", app.application.id)
                    print(datetime.now())

                    try:
                        self.send_update_email(app)
                    except SMTPException as stmp_e:
                        print(stmp_e)
                        print("Not able to send email due to smtp exception.")
                    except Exception as e:
                        print(e)
                        print("Not able to send email.")

                    time.sleep(5)


        if options['humbolt_denial']:
            application_statuses = ApplicationStatus.objects.all()

            print("Emails sent to:")
            for app in application_statuses:
                if app.current_step:
                        if app.current_step.step == 2 and app.denied == False and app.lot.address.ward == '27' and app.lot.address.community == 'HUMBOLDT PARK':

                            print(app.application.first_name, app.application.last_name, " - Application ID", app.application.id)
                            print(datetime.now())

                            # try:
                            #     self.send_denial_humbolt_email(app)
                            # except SMTPException as stmp_e:
                            #     print(stmp_e)
                            #     print("Not able to send email due to smtp exception.")
                            # except Exception as e:
                            #     print(e)
                            #     print("Not able to send email.")

                            # time.sleep(5)


    def send_deed_email(self, application):
        context = {
            'app': application,
            'lots': application.lot_set.all()
        }

        html_template = get_template('deed_inquiry_email.html')
        txt_template = get_template('deed_inquiry_email.txt')

        html_content = html_template.render(context)
        txt_content = txt_template.render(context)

        msg = EmailMultiAlternatives('Important notice from Large Lots',
                                txt_content,
                                settings.EMAIL_HOST_USER,
                                [application.email])

        msg.attach_alternative(html_content, 'text/html')
        msg.send()


    def send_update_email(self, application_status):
        context = {
            'app': application_status.application,
            'lot': application_status.lot
        }

        html_template = get_template('update_email.html')
        txt_template = get_template('update_email.txt')

        html_content = html_template.render(context)
        txt_content = txt_template.render(context)

        msg = EmailMultiAlternatives('Important update from Large Lots',
                                txt_content,
                                settings.EMAIL_HOST_USER,
                                [application_status.application.email])

        msg.attach_alternative(html_content, 'text/html')
        msg.send()


    def send_wintrust_email(self, application_status):
        context = {
            'app': application_status.application,
            'lot': application_status.lot
        }

        html_template = get_template('wintrust_email.html')
        txt_template = get_template('wintrust_email.txt')

        html_content = html_template.render(context)
        txt_content = txt_template.render(context)

        msg = EmailMultiAlternatives('Special event for Large Lots applicants',
                                txt_content,
                                settings.EMAIL_HOST_USER,
                                [application_status.application.email])

        msg.attach_alternative(html_content, 'text/html')
        msg.send()


    def send_denial_humbolt_email(self, application_status):
        context = {
            'app': application_status.application,
            'lot': application_status.lot
        }

        html_template = get_template('denial_humbolt_email.html')
        txt_template = get_template('denial_humbolt_email.txt')

        html_content = html_template.render(context)
        txt_content = txt_template.render(context)

        msg = EmailMultiAlternatives('Large Lots Application',
                                txt_content,
                                settings.EMAIL_HOST_USER,
                                [application_status.application.email])

        msg.attach_alternative(html_content, 'text/html')
        msg.send()

    def send_denial_garfield_email(self, application_status):
        context = {
            'app': application_status.application,
            'lot': application_status.lot
        }

        html_template = get_template('denial_garfield_email.html')
        txt_template = get_template('denial_garfield_email.txt')

        html_content = html_template.render(context)
        txt_content = txt_template.render(context)

        msg = EmailMultiAlternatives('Large Lots Application',
                                txt_content,
                                settings.EMAIL_HOST_USER,
                                [application_status.application.email])

        msg.attach_alternative(html_content, 'text/html')
        msg.send()
