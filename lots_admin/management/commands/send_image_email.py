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
            if application.deed_image == '' and '3' in wards and application.id not in [65, 76, 114, 98, 279, 301, 303, 304, 306, 1224, 387, 442, 469, 489, 462, 506, 547, 571, 588, 596, 601, 610, 640, 638, 722, 726, 759, 786, 806, 820, 823, 872, 894, 897, 908, 943, 946, 969, 990, 1223, 1024, 1042, 1076, 1089, 1110, 1138, 1139, 1175, 1229, 1232, 1257, 1258, 1306, 1317, 1315, 1395, 1424, 1432, 1456, 1488, 1525, 1544, 1550, 1569, 1578, 1615, 1627, 1683, 1742, 1755, 1774, 1849, 1860, 1861, 1911, 1924, 1936, 1937, 1940, 1944, 1959, 2000]
            # if application.id == 46 or application.id == 2268:
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
