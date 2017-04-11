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
            blank_deeds = [329, 2602, 1693, 1788, 1530, 1434, 672, 206, 1140, 2200, 2110, 2376, 444, 2310, 1696, 2048, 2045, 2047, 2049, 2052, 1402, 1651, 163, 2599, 672, 2048, 2147, 1651, 206, 1140, 1001, 1004, 2200, 2110, 2310, 444, 1693, 2539, 2554, 329, 2604, 1530, 1434, 1512, 2113, 281, 1522, 2673, 2599, 2104, 622, 1473, 978, 984, 2579, 1788, 1696, 2045, 2052, 1954, 2658, 2016, 2607, 816, 1405, 53, 163, 2116, 2117, 150]

            if application.deed_image == '' and application.id == 1758:
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
