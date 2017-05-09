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


    def handle(self, *args, **options):
        if options['wintrust_email']:
            application_statuses = ApplicationStatus.objects.all()

            print("Emails sent to:")
            for app in application_statuses:
                if app.current_step:
                        if app.current_step.step in [4, 6] and app.denied == False and app.application.id > 996 and app.application.id <= 1800:

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

                            time.sleep(3)


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

                # if application.deed_image == '' and wards != ['27', '27'] and application.id > 1268:
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
                reviews = Review.objects.filter(application=app.id)

                if reviews:
                    last_email_sent = datetime(2017, 4, 30, 12, 30, 00).replace(tzinfo=None)
                    latest_review = reviews.latest('created_at').created_at.replace(tzinfo=None)

                    if app.current_step:
                        if app.current_step.step in [4, 6] and app.denied == False and latest_review > last_email_sent:

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

                            time.sleep(3)

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

        msg.attach_file('lots/static/images/Everyday_Loan_LargeLot.pdf')
        msg.attach_file('lots/static/images/Invitation_LargeLot_Workshop.pdf')

        msg.attach_alternative(html_content, 'text/html')
        msg.send()
