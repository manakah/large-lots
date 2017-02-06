from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings

from lots_admin.models import Application

class Command(BaseCommand):
    help = 'Remove potentially malicious things from uploaded files'

    def handle(self, *args, **options):
        applications = Application.objects.all()

        for application in applications:
            if application.deed_image == '':
                self.send_email(application)
    
    def send_email(self, application):
        context = {
            'app': application,
            'lots': application.lot_set.all()
        }
        
        html_template = get_template('deed_upload_email.html')
        txt_template = get_template('deed_upload_email.txt')

        html_content = html_template.render(context)
        txt_content = txt_template.render(context)
        
        msg = EmailAlternatives('Special notice from Large Lots',
                                txt_content,
                                settings.EMAIL_HOST_USER,
                                [application.email])

        msg.attach_alternative(html_content, 'text/html')
        msg.send()
