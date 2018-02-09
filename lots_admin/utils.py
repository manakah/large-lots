from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings

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

    # try:
    #     msg.send()
    # except SMTPException as stmp_e:
    #     print(stmp_e)
    #     print("Not able to send email due to smtp exception.")
    # except Exception as e:
    #     print(e)
    #     print("Not able to send email.")

    # time.sleep(5)