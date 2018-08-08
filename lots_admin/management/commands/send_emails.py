from datetime import datetime
from functools import partialmethod
from itertools import chain
from smtplib import SMTPException
import time

from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings
from django.db import connection

from lots_admin.models import Application, ApplicationStatus, ApplicationStep, Review, DenialReason, User
from lots_admin.look_ups import DENIAL_REASONS


class Command(BaseCommand):
    help = 'Send bulk emails to Large Lots applicants. By default, all applications ' + \
        'associated with an email address will be aggregated, and one email will ' + \
        'be sent. See --separate_emails for handling shared email addresses.'

    def add_arguments(self, parser):
        # Meta options
        parser.add_argument('--date',
                            help='Date in format YYYY-MM-DD for emails, etc.')

        parser.add_argument('--separate_emails',
                            help='Comma-separated list of email addresses. ' +
                                 'In contrast to the default behavior of one aggregate ' +
                                 'email, separate emails will be sent for each ' +
                                 'application associated with the provided email ' +
                                 'addresses. This is useful when one email address ' +
                                 'is in use by more than one applicant.',
                            default='')

        parser.add_argument('--n',
                            help='Set number of emails to send.',
                            default=-1)

        # Select options
        parser.add_argument('--wintrust_email',
                            action='store_true',
                            help='Send emails about a special event')

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

        parser.add_argument('--closing_invitations_email',
                            action='store_true',
                            help='Send closing invitations to applicants')

        parser.add_argument('--eds_denial_email',
                            action='store_true',
                            help='Send denial emails to applicants who did not submit EDS')

    def handle(self, *args, **options):
        self.date = options['date']
        self.separate_emails = options['separate_emails'].split(',')
        self.n = int(options['n'])

        for email in (k for k, v in options.items() if k.endswith('email') and v is True):
            getattr(self, 'send_{}'.format(email))()

    def _select_applicants(self, operator, step, **keywords):
        '''
        Build and execute a query to select applicants, grouped by email and
        ordered by applicant name.

        Return a tuple, (email, Application queryset, ApplicationStatus queryset),
        such that the returned Application and ApplicationStatus objects meet
        the criteria of the query.
        '''
        applicant_select = '''
            WITH applicants AS (
              SELECT
                app.email,
                app.id AS app_id,
                status.id AS status_id,
                step.step
              FROM lots_admin_application AS app
              JOIN lots_admin_applicationstatus as status
              ON app.id = status.application_id
              JOIN lots_admin_applicationstep as step
              ON status.current_step_id = step.id
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
            GROUP BY email
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
        except SMTPException as stmp_e:
            print(stmp_e)
            print("Not able to send email due to smtp exception.")
        except Exception as e:
            print(e)
            print("Not able to send email.")

        time.sleep(5)

    def _log(self, app, statuses, log_fmt=None, **kwargs):
        if not log_fmt:
            log_fmt = '{date} {applicant} {email} {phone} {pins}'

        log_kwargs = dict(
            date=datetime.now().strftime('%Y-%m-%d %H:%M'),
            applicant=' '.join([app.first_name, app.last_name]),
            email=app.email,
            phone=app.phone,
            pins=', #'.join(str(s.lot.pin) for s in statuses),
        )

        log_kwargs.update(kwargs)

        print(log_fmt.format(**log_kwargs))

    def _deny(self, app_status, denial_reason, admin_user):
        '''
        Deny the given application and create a corresponding review object.

        :app_status - ApplicationStatus object
        :denial_reason - DenialReason object
        :admin_user - User object (usually, an admin)
        '''
        app_status.denied = True
        app_status.current_step = None
        app_status.save()

        review = Review(reviewer=admin_user,
                        denial_reason=denial_reason,
                        application=app_status,
                        email_sent=True)

        review.save()

    def _date_to_datetime(self, hour, minute):
        date = datetime.strptime(self.date, '%Y-%m-%d')

        date_parts = [getattr(date, k) for k in ('year', 'month', 'day')]
        date_parts += [hour, minute]

        return datetime(*date_parts)

    def send_wintrust_email(self):
        '''
        Send event invitations on a per-application basis.
        '''
        subject = 'Special event for Large Lots applicants'

        for email, apps, statuses in chain(self._select_applicants_on_step(4),
                                           self._select_applicants_on_step(6)):
            for app in apps:
                context = {'app': app}
                self._send_email('wintrust_email', subject, email, context)
                self._log(app, statuses.filter(application=app))

    def send_eds_email(self):
        '''
        Send EDS invitations on a per-email basis, unless specified by the admin.

        Email only applicants whose non-denied applications are all on step 7,
        in order to avoid a situation where an applicant has active application
        statuses on other steps, as these will get stuck if the applicant
        submits an EDS before the remaining statuses reach step 7.
        '''
        subject = 'LargeLots application - Economic Disclosure Statement (EDS)'

        for email, apps, statuses in self._select_applicants_on_step(7, every_status=True, filter='app.eds_sent = FALSE'):
            send_one = True

            if email in self.separate_emails:
                send_one = False

            for app in apps:
                context = {'app': app}
                self._send_email('eds_email', subject, email, context)
                self._log(app, statuses)

                if send_one:
                    break

            for app in apps:
                app.eds_sent = True
                app.save()

    def send_lotto_email(self):
        '''
        Send a lottery notification on a per-status basis, since all lots
        will have their own lottery event.
        '''
        subject = 'LargeLots application - Lottery'
        log_fmt = '{date} {applicant} ({email}, {phone}) invited to Lottery {event} for lots #{pins}'

        # Sort applicants by lot PIN
        applicants = []

        for email, apps, statuses in self._select_applicants_on_step(6, filter='status.lottery_email_sent = FALSE'):
            for status in statuses:
                app_data = (email, apps.get(applicationstatus=status), status)
                applicants.append(app_data)

        sorted_applicants = sorted(list(applicants), key=lambda x: x[2].lot.pin)

        for idx, app_data in enumerate(sorted_applicants[:self.n], start=1):
            email, app, status = app_data

            if idx <= len(sorted_applicants) / 2:
                event = self._date_to_datetime(hour=9, minute=0)
            else:
                event = self._date_to_datetime(hour=13, minute=0)

            context = {
                'lot': status.lot,
                'app': app,
                'date': event,
                'time': None,
            }

            self._send_email('lottery_notification', subject, email, context)

            status.lottery_email_sent = True
            status.save()

            self._log(app, [status], log_fmt, event=event)

    def send_eds_final_email(self):
        '''
        Send EDS final notice on a per-email basis, unless specified by the
        admin.
        '''
        subject = 'LargeLots application - Economic Disclosure Statement (EDS)'

        for email, apps, statuses in self._select_applicants_on_step(7):
            send_one = True

            if email in self.separate_emails:
                send_one = False

            for app in apps:
                context = {'app': app}
                self._send_email('eds_email', subject, app.email, context)
                self._log(app, statuses.filter(application=app))

                if send_one:
                    break

    def send_closing_time_email(self):
        '''
        Send closing time notifications on a per-email basis.
        '''
        subject = 'Closing Time for Large Lots'

        next_step = ApplicationStep.objects.get(step=9)

        for email, apps, statuses in self._select_applicants_on_step(8):
            lots = [s.lot for s in statuses]

            context = {'app': apps.first(), 'lots': lots}
            self._send_email('closing_time_email', subject, email, context)
            self._log(apps.first(), statuses)

            for status in statuses:
                status.current_step = next_step
                status.save()

    def send_closing_invitations_email(self):
        '''
        Send invitations to closings on a per-email basis.
        '''
        subject = 'Large Lot Closing Date and Time'
        log_fmt = '{date} {applicant} ({email}, {phone}) invited to Closing {event} for lots #{pins}'

        applicants = list(self._select_applicants_on_step(10, filter='app.closing_invite_sent = FALSE'))

        for idx, app_data in enumerate(applicants[:self.n], start=1):
            email, apps, statuses = app_data

            lots = [s.lot for s in statuses]

            if idx <= len(applicants) / 2:
                event = self._date_to_datetime(hour=9, minute=0)
            else:
                event = self._date_to_datetime(hour=13, minute=0)

            context = {'app': apps.first(), 'lots': lots, 'event': event}
            self._send_email('closing_invitation_email', subject, email, context)

            for app in apps:
                app.closing_invite_sent = True
                app.save()

            self._log(app, statuses, log_fmt, event=event)

    def send_eds_denial_email(self):
        '''
        Send denials on a per-email address basis, unless specified by the
        admin.
        '''
        subject = 'LargeLots application - Denial'
        log_fmt = '{date} {applicant} ({email}) denied due to lack of EDS for lots #{pins}'

        no_eds, _ = DenialReason.objects.get_or_create(value=DENIAL_REASONS['EDS'])
        admin_user = User.objects.get(id=5)

        for email, apps, statuses in self._select_applicants_on_step(7):
            send_one = True

            if email in self.separate_emails:
                send_one = False

            for app in apps:
                if send_one:
                    lots = [s.lot for s in statuses]
                else:
                    lots = [s.lot for s in statuses.filter(application=app)]

                context = {'app': app, 'lots': lots}
                self._send_email('eds_denial_email', subject, email, context)
                self._log(app, statuses, log_fmt)

                if send_one:
                    break

            for status in statuses:
                self._deny(status, no_eds, admin_user)
