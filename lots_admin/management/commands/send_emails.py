from datetime import datetime
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
                                 'is in use by more than one applicant.')

        parser.add_argument('--lotto_offset',
                            help='Set SQL offset.')

        # Select options
        parser.add_argument('--wintrust_email',
                            action='store_true',
                            help='Send emails about a special event')

        parser.add_argument('--eds_email',
                            help='Send email with link to complete EDS')

        parser.add_argument('--lotto_email',
                            help='Send email with notification of lottery. Use one of two arguments: morning or afternoon.')

        parser.add_argument('--eds_final_email',
                            action='store_true',
                            help='Send email to all applicants on Step 7.')

        parser.add_argument('--closing_time',
                            action='store_true',
                            help='Send closing notifications to applicants')

        parser.add_argument('--closing_invitations',
                            help='Send closing invitations to applicants')

        parser.add_argument('--eds_denial',
                            action='store_true',
                            help='Send denial emails to applicants who did not submit EDS')

    def handle(self, *args, **options):
        if options['wintrust_email']:
            for app, statuses in chain(self._select_applicants_on_step(4),
                                       self._select_applicants_on_step(6)):

                context = {'app': app}

                self._send_email('wintrust_email',
                                 'Special event for Large Lots applicants',
                                 app.email,
                                 context)

                self._log(app, statuses)

        if options['eds_email']:
            for app, statuses in self._select_applicants_on_step(7, every_status=True, filter='app.eds_sent = FALSE'):
                '''
                TO-DO: Only send one invitation per email?
                '''
                context = {'app': app}

                self._send_email('eds_email',
                                 'LargeLots application - Economic Disclosure Statement (EDS)',
                                 app.email,
                                 context)

                app.eds_sent = True
                app.save()

                self._log(app, statuses)

        if options['lotto_email']:
            for app, statuses in self._select_applicants_on_step(6, filter='status.lottery_email_sent = FALSE'):
                '''
                TO-DO: Set pool size, and divide by 2.
                '''
                for status in statuses:
                    context = {
                        'lot': status.lot,
                        'app': app,
                        'date': None,
                        'time': None,
                    }

                    self._send_email('lottery_notification',
                                     'LargeLots application - Lottery',
                                     app.email,
                                     context)

                    status.lottery_email_sent = True
                    status.save()

                self._log(app, statuses)

        if options['eds_final_email']:
            for app, statuses in self._select_applicants_on_step(7):
                context = {'app': app}

                self.send_email('eds_email',
                                'LargeLots application - Economic Disclosure Statement (EDS)',
                                app.email,
                                context)

                self._log(app, statuses)

        if options['closing_time']:
            for app, statuses in self._select_applicants_on_step(8):
                context = {
                    'app': app,
                    'lots': [s.lot for s in statuses],
                }

                self.send_email('closing_time_email',
                                'Closing Time for Large Lots',
                                app.email,
                                context)

                next_step = ApplicationStep.objects.get(step=9)

                for status in statuses:
                    status.current_step = next_step
                    status.save()

                self._log(app, statuses)

        if options['closing_invitations']:
            date = datetime.strptime(options['date'], '%Y-%m-%d')
            applicants = self._select_applicants_on_step(10, filter='app.closing_invite_sent = FALSE')
            sorted_applicants = sorted(list(applicants), key=lambda x: (x[0].last_name, x[0].first_name))

            log_fmt = '{date} {applicant} ({email}, {phone}) invited to ' + \
                      'Closing {event} for lots #{pins}'

            for idx, app_stuff in enumerate(sorted_applicants, start=1):
                app, statuses = app_stuff
                lots = [s.lot for s in statuses]

                date_parts = [getattr(date, k) for k in ('year', 'month', 'day')]

                # Invite half the applicants to the morning event, and
                # half to the afternoon event, using len of applicant list
                # rather than initial n to handle case where we get fewer
                # than n applicants.
                if idx <= len(sorted_applicants) / 2:
                    date_parts += [9, 0]
                    event = datetime(*date_parts)
                else:
                    date_parts += [13, 0]
                    event = datetime(*date_parts)

                context = {
                    'app': app,
                    'lots': lots,
                    'event': event,
                }

                self._send_email('closing_invitation_email',
                                 'Large Lot Closing Date and Time',
                                 app.email,
                                 context)

                app.closing_invite_sent = True
                app.save()

                self._log(app, statuses, log_fmt, event=event)

        if options['eds_denial']:
            # Set up denial globals
            no_eds, _ = DenialReason.objects.get_or_create(value=DENIAL_REASONS['EDS'])
            admin_user = User.objects.get(id=5)

            log_fmt = '{date} {applicant} ({email}) denied due to ' + \
                      'lack of EDS for lots #{pins}'

            for app, statuses in self._select_applicants_on_step(7):
                context = {
                    'app': app,
                    'lots': [s.lot for s in statuses]
                }

                self._send_email('eds_denial_email',
                                 'LargeLots application - Denial',
                                 app.email,
                                 context)

                self._log(app, statuses, log_fmt)

                for status in statuses:
                    self._deny(status, no_eds, admin_user)

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

    def _filter_string(self, filter_parts):
        return ' AND '.join(filter(None, filter_parts))

    def _select_applicants_on_step(self, step, **kwargs):
        denied_filter = 'status.denied = FALSE'
        step_filter = 'step.step = {step}'.format(step=step)

        status_filter = self._filter_string([
            denied_filter,
            step_filter,
            kwargs.get('filter'),
        ])

        applicant_select = '''
            SELECT
              app.id,
              ARRAY_AGG(status.id) AS app_statuses
            FROM lots_admin_application AS app
            JOIN lots_admin_applicationstatus as status
            ON app.id = status.application_id
            JOIN lots_admin_applicationstep as step
            ON status.current_step_id = step.id
            WHERE {filter}
            GROUP BY app.id
        '''.format(filter=status_filter)

        if kwargs.get('every_status'):
            applicant_select += 'HAVING EVERY({step})'.format(step=step_filter)

        # print(applicant_select)

        with connection.cursor() as cursor:
            cursor.execute(applicant_select)

            for app, statuses in cursor:
                application = Application.objects.get(id=app)
                statuses = [ApplicationStatus.objects.get(id=s) for s in statuses]
                yield application, statuses

    def _select_applicants_not_on_step(self, step, **kwargs):
        pass

    def _select_applicants_on_steps_before(self, step, **kwargs):
        pass

    def _select_applicants_on_steps_after(self, step, **kwargs):
        pass

    def _deny(self, app_status, denial_reason, admin_user):
        '''
        Deny the given application and create a corresponding review
        object.

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
