from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings

from smtplib import SMTPException
import time
from datetime import datetime

from lots_admin.models import Application, ApplicationStatus

class Command(BaseCommand):
    help = 'Send emails to applicants who need to resubmit deeds'


    def add_arguments(self, parser):
        parser.add_argument('--deed_upload',
                            action='store_true',
                            help='Send emails to applicants who need to resubmit a deed')

        parser.add_argument('--update_email',
                            action='store_true',
                            help='Send emails to insure applicants that "everything is okay"')


    def handle(self, *args, **options):

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

                if application.deed_image == '' and wards != ['27', '27'] and application.id > 1268:
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
                # For next round...
                # Find all reviews for an application.
                # Find the most recent review.
                # Get that timestamp.
                # reviews = Review.objects.filter(application=app.id)
                # reviews.latest('created_at') > datetime.datetime(2017, 4, 28, 12, 30, 00)
                # 12:30 on April 28, 2017...workout comparison logic....
                if app.current_step:
                    if app.current_step.step in [4, 6] and app.denied == False:

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

