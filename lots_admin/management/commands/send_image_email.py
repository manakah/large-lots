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
            application_status_objs = ApplicationStatus.objects.filter(application_id=application.id)
            wards = []
            for status in application_status_objs:
                wards.append(status.lot.address.ward)

            # if application.deed_image == '' and '27' not in wards:
            # Ward numbers.
            sent_emails = ['3', '4', '5', '6', '7', '8', '9', '20', '34', '10', '11', '15', '16', '17', '18', '19', '21', '22', '24', '26', '28', '29', '37']

            try:
                first_ward = wards[0]
            except:
                first_ward = ''

            try:
                second_ward = wards[1]
            except:
                second_ward = ''

            # if application.deed_image == '' and '37' in wards and first_ward not in sent_emails and second_ward not in sent_emails:
            blank_deeds = [1330, 1332, 1205, 2015, 2696, 1395, 575, 2723, 1473, 168, 562, 331, 2170, 1607, 301, 2180, 1128, 2422, 19, 2565, 578, 1405, 676, 1725, 497]

            if application.deed_image == '' and application.id in blank_deeds:
                print(application.first_name, application.last_name, " - Application ID", application.id)
                print('Wards:', wards)
                try:
                    self.send_email(application)
                except:
                    print("Not able to send email.")


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
