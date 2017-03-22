from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings

from lots_admin.models import Application, ApplicationStatus

class Command(BaseCommand):
    help = 'Send emails to applicants who need to resubmit deeds'

    def handle(self, *args, **options):
        applications = Application.objects.all()

        print("Emails sent to:")
        for application in applications:
            # Check for ward 27.
            application_status_objs = ApplicationStatus.objects.filter(application_id=application.id)
            wards = []
            for status in application_status_objs:
                wards.append(status.lot.address.ward)

            # if application.deed_image == '' and '27' not in wards:
            if application.deed_image == '' and '3' in wards:
            # if application.id == 46 or application.id == 2268:
                print(application.first_name, application.last_name, " - Application ID", application.id)
                print('Wards:', wards)
                self.send_email(application)


    def send_email(self, application):
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
