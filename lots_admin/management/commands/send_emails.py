from datetime import datetime
from functools import partialmethod
from itertools import chain
import json
from smtplib import SMTPException
import time
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings
from django.db import connection
from django.template import Context, Template

import logging
from raven.handlers.logging import SentryHandler
from raven.conf import setup_logging

from lots_admin.models import Application, ApplicationStatus, ApplicationStep, Review, DenialReason, User
from lots_admin.look_ups import DENIAL_REASONS


logger = logging.getLogger(__name__)
handler = SentryHandler(settings.SENTRY_DSN)
handler.setLevel(logging.ERROR)
setup_logging(handler)


class CannotSendEmailException(Exception):
    pass


class Command(BaseCommand):
    help = 'Send bulk emails to Large Lots applicants.'

    def add_arguments(self, parser):
        '''
        To send a new email, add a Boolean argument called 'x_email' here, then
        write a method on the Command class called 'send_x_email'.
        '''
        # Meta options
        parser.add_argument('-n', '--number-to-send',
                            help='Set number of emails to send.',
                            type=int,
                            default=0)

        parser.add_argument('-a', '--admin',
                            help='The ID of the admin sending the emails.',
                            type=int)

        parser.add_argument('--base_context',
                            help='A string-encoded JSON object of values for' +
                            'email template context.',
                            default=r'{}')

        # Select options
        parser.add_argument('--eds_email',
                            action='store_true',
                            help='Send email with link to complete EDS')

        parser.add_argument('--lotto_email',
                            action='store_true',
                            help='Send email with notification of lottery')

        parser.add_argument('--eds_final_email',
                            action='store_true',
                            help='Send email to all applicants on Step 7')

        parser.add_argument('--closing_time_email',
                            action='store_true',
                            help='Send closing notifications to applicants')

        parser.add_argument('--eds_denial_email',
                            action='store_true',
                            help='Send denial emails to applicants who did' +
                            'not submit EDS')

        parser.add_argument('--custom_email',
                            help='Send a custom email to applicants on or' +
                            'not on a given step. Accepted values: on_step,' +
                            'not_on_step, on_steps_before, on_steps_after')

        parser.add_argument('--steps',
                            help='Required when sending a custom email.' +
                            'Step used to select applicants to email.',
                            type=int)

        parser.add_argument('--every_status',
                            help='Send emails to applicants who have all applications' + 
                            'on the same step.',
                            action='store_true',
                            default=False)

    def handle(self, *args, **options):
        if options['number_to_send']:
            self.n = options['number_to_send']

        self.base_context = json.loads(options['base_context'])
        self.admin = User.objects.get(id=options['admin'])

        try:
            self.email_command, = (k for k, v in options.items() if k.endswith('email') and v)
        except ValueError:
            raise CommandError('Only specify one email to send at a time.')

        if self.email_command == 'custom_email':
            self.operator = options['custom_email']
            self.step = options['steps']
            self.every_status = options['every_status']

        getattr(self, 'send_{}'.format(self.email_command))()

    def _select_applicants(self, operator, step, **keywords):
        '''
        Build and execute a query to select applicants, grouped by email, name,
        and ZIP code (a rough unique identifier of individuals) and ordered by
        applicant name.

        Return a tuple, (email, Application queryset, ApplicationStatus queryset),
        such that the returned Application and ApplicationStatus objects meet
        the criteria of the query.
        '''
        applicant_select = '''
            WITH applicants AS (
              SELECT
                app.email,
                app.first_name,
                app.last_name,
                address.zip_code,
                app.id AS app_id,
                status.id AS status_id,
                step.step
              FROM lots_admin_application AS app
              JOIN lots_admin_applicationstatus AS status
              ON app.id = status.application_id
              JOIN lots_admin_applicationstep AS step
              ON status.current_step_id = step.id
              JOIN lots_admin_address AS address
              ON app.contact_address_id = address.id
              WHERE status.denied = FALSE
              {filter}
              ORDER BY app.last_name, app.first_name
            )
            SELECT
              email,
              ARRAY_AGG(app_id) AS apps,
              ARRAY_AGG(status_id) AS app_statuses
            FROM applicants
            {where}
            GROUP BY email, first_name, last_name, zip_code
            {having}
        '''

        select_kwargs = {}

        if keywords.get('filter'):
            select_kwargs['filter'] = 'AND {}'.format(keywords['filter'])
        else:
            select_kwargs['filter'] = ''

        step_kwargs = {'operator': operator, 'step': step}

        if keywords.get('every_status'):
            where = ''
            having = 'HAVING EVERY(step {operator} {step})'.format(**step_kwargs)
        else:
            where = 'WHERE step {operator} {step}'.format(**step_kwargs)
            having = ''

        select_kwargs.update({'where': where, 'having': having})

        with connection.cursor() as cursor:
            cursor.execute(applicant_select.format(**select_kwargs))

            for email, apps, statuses in cursor:
                apps = Application.objects.filter(id__in=apps)
                statuses = ApplicationStatus.objects.filter(id__in=statuses)
                yield email, apps, statuses

    _select_applicants_on_step = partialmethod(_select_applicants, '=')
    _select_applicants_not_on_step = partialmethod(_select_applicants, '!=')
    _select_applicants_on_steps_before = partialmethod(_select_applicants, '<')
    _select_applicants_on_steps_after = partialmethod(_select_applicants, '>')

    def _send_email(self, template, subject, email_address, context):
        html_template = get_template('emails/{}.html'.format(template))
        txt_template = get_template('emails/{}.txt'.format(template))

        html_content = html_template.render(context)
        txt_content = txt_template.render(context)

        msg = EmailMultiAlternatives(subject,
                                     txt_content,
                                     settings.EMAIL_HOST_USER,
                                     [email_address])

        msg.attach_alternative(html_content, 'text/html')

        try:
            msg.send()

        except SMTPException as smtp_e:
            logging.error(
                "Not able to send email due to SMTP exception.",
                extra={
                    'exception': smtp_e,
                    'email_address': email_address,
                    'subject': subject,
                }
            )
            raise CannotSendEmailException(smtp_e)

        except Exception as e:
            logging.error(
                "Not able to send email due to unknown exception.",
                extra={
                    'exception': e,
                    'email_address': email_address,
                    'subject': subject,
                }
            )
            raise CannotSendEmailException(e)


    def _log(self, app, statuses, log_fmt=None, **kwargs):
        if not log_fmt:
            log_fmt = '{date} | {command} | {application} | {applicant} | {email} | {phone} | {pins}'

        log_kwargs = dict(
            date=datetime.now().strftime('%Y-%m-%d %H:%M'),
            command=self.email_command,
            application = app.id,
            applicant=' '.join([app.first_name, app.last_name]),
            email=app.email,
            phone=app.phone,
            pins=','.join(str(s.lot.pin) for s in statuses),
        )

        log_kwargs.update(kwargs)

        logging.info(log_fmt.format(**log_kwargs))

    def _write_to_stdout(self, app_status_id, error):
        self.stdout.write('{0}|{1}'.format(app_status_id, error))

    def _deny(self, app_status, denial_reason):
        '''
        Deny the given application and create a corresponding review object.

        :app_status - ApplicationStatus object
        :denial_reason - DenialReason object
        '''
        app_status.denied = True
        app_status.current_step = None
        app_status.save()

        review = Review(reviewer=self.admin,
                        denial_reason=denial_reason,
                        application=app_status,
                        email_sent=True)

        review.save()

    def send_eds_email(self):
        '''
        Email only applicants whose non-denied applications are all on step 7,
        in order to avoid a situation where an applicant has active application
        statuses on other steps, as these will get stuck if the applicant
        submits an EDS before the remaining statuses reach step 7.
        '''
        subject = 'LargeLots application - Economic Disclosure Statement (EDS)'

        for email, apps, statuses in self._select_applicants_on_step(7, every_status=True, filter='app.eds_sent = FALSE'):
            context = {'app': apps.first()}
            context.update(self.base_context)
            try:
                self._send_email('eds_email', subject, email, context)

            except CannotSendEmailException as error:
                for a in apps:
                    self._write_to_stdout(a.id, error)

            else:
                self._log(apps.first(), statuses)

                for app in apps:
                    app.eds_sent = True
                    app.save()

    def send_eds_final_email(self):
        subject = 'LargeLots application - Economic Disclosure Statement (EDS)' 
        for email, apps, statuses in self._select_applicants_on_step(7):
            context = {'app': apps.first()}
            context.update(self.base_context)

            try:
                self._send_email('eds_email', subject, email, context)

            except CannotSendEmailException as error:
                for a in apps:
                    self._write_to_stdout(a.id, error)

            else:
                self._log(apps.first(), statuses)

                for app in apps:
                    app.eds_sent = True
                    app.save()

    def send_eds_denial_email(self):
        subject = 'LargeLots application - Denial'
        log_fmt = '{date} {applicant} ({email}) denied due to lack of EDS for lots {pins}'

        no_eds, _ = DenialReason.objects.get_or_create(value=DENIAL_REASONS['EDS'])

        for email, apps, statuses in self._select_applicants_on_step(7):
            lots = [s.lot for s in statuses]
            context = {'app': apps.first(), 'lots': lots}

            try:
                self._send_email('eds_denial_email', subject, email, context)

            except CannotSendEmailException as error:
                for a in apps:
                    self._write_to_stdout(a.id, error)
            else:
                self._log(apps.first(), statuses, log_fmt)

                for status in statuses:
                    self._deny(status, no_eds)
                    
    def send_lotto_email(self):
        '''
        Send a lottery notification on a per-status basis, since all lots
        will have their own lottery event.
        '''
        subject = 'LargeLots application - Lottery'
        log_fmt = '{date} {applicant} ({email}, {phone}) invited to Lottery at {event} for lots {pins}'

        # https://docs.python.org/3/library/collections.html#defaultdict-examples
        lots_with_apps = defaultdict(list)

        for email, apps, statuses in self._select_applicants_on_step(6, filter='status.lottery_email_sent = FALSE'):
            for status in statuses:
                app_data = (email, apps.get(applicationstatus=status), status)
                lots_with_apps[status.lot.pin].append(app_data)

        ordered_lots_with_apps = sorted(lots_with_apps.items())
        
        for lot, app_collection in ordered_lots_with_apps[:self.n]:
            for app_data in app_collection:
                email, app, status = app_data

                context = {'lot': status.lot, 'app': app}
                context.update(self.base_context)

                try:
                    self._send_email('lottery_notification', subject, email, context)

                except CannotSendEmailException as error:
                    self._write_to_stdout(app.id, error)

                else:
                    event = ' on '.join([context['time'], context['date']])
                    self._log(app, [status], log_fmt, event=event)

                    status.lottery_email_sent = True
                    status.save()

    def send_closing_time_email(self):
        subject = 'Closing Time for Large Lots'

        next_step = ApplicationStep.objects.get(step=9)

        for email, apps, statuses in self._select_applicants_on_step(8):
            lots = [s.lot for s in statuses]

            context = {'app': apps.first(), 'lots': lots}

            try:
                self._send_email('closing_time_email', subject, email, context)

            except CannotSendEmailException as error:
                for a in apps:
                    self._write_to_stdout(a.id, error)

            else:
                self._log(apps.first(), statuses)

                for status in statuses:
                    status.current_step = next_step
                    status.save()

                    review_blob = {
                        'reviewer': self.admin,
                        'email_sent': False,
                        'application': status,
                        'step_completed': 9,
                    }

                    Review.objects.create(**review_blob)

    def send_custom_email(self):
        '''
        e.g., python manage.py send_emails --custom_email on_step --step 6 --every_status
        '''
        select_method = getattr(self, '_select_applicants_{}'.format(self.operator))

        for email, apps, statuses in select_method(self.step, every_status=self.every_status):
            lots = [s.lot for s in statuses]
            context = {'app': apps.first(), 'lots': lots}
            context.update(self.base_context)

            # Render the email text here, if the user includes variables, e.g., app.tracking_id
            partial_template = Template(self.base_context['email_text'])
            partial_context = Context({'app': apps.first()})
            rendered_text = partial_template.render(partial_context)
            context.update({'email_text': rendered_text})

            try:
                self._send_email('custom_email', context['subject'], email, context)

            except CannotSendEmailException as error:
                for a in apps:
                    self._write_to_stdout(a.id, error)

            else:
                self._log(apps.first(), statuses)
