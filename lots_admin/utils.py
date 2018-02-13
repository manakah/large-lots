from datetime import datetime
import urllib.parse

from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings

from lots_admin.look_ups import DENIAL_REASONS
from lots_admin.models import Review

def create_email_msg(template_name, email_subject, email_to_address, context):
    html_template = get_template('emails/{}.html'.format(template_name))
    txt_template = get_template('emails/{}.txt'.format(template_name))

    html_content = html_template.render(context)
    txt_content = txt_template.render(context)

    msg = EmailMultiAlternatives(email_subject,
                            txt_content,
                            settings.EMAIL_HOST_USER,
                            [email_to_address])

    msg.attach_alternative(html_content, 'text/html')

    return msg

def send_denial_email(request, application_status):
    context = {'app': application_status.application, 
               'lot': application_status.lot,
               'review': Review.objects.filter(application=application_status).latest('id'),
               'today': datetime.now().date(),
               'DENIAL_REASONS': DENIAL_REASONS
               }

    msg = create_email_msg(
        'denial_email', 
        'Notification from LargeLots', 
        application_status.application.email, 
        context
    )

    msg.send()

def create_redirect_path(request):
    params = {k: request.session[k] for k in ('page', 'query') if request.session.get(k)}

    return '?' + urllib.parse.urlencode(params)
