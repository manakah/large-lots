import json
import logging
import pytest
from unittest.mock import patch
import sys

from django.core.management import call_command
from django.db.models import Q
from django.core.urlresolvers import reverse
from ..test_config import CURRENT_PILOT

from lots_admin.models import Application, ApplicationStatus
from lots_admin.management.commands.send_emails import Command, CannotSendEmailException


class TestEdsEmail:
    '''
    Test that we appropriately select and notify Rivers Cuomo
    and Karen Oh, and update their active applications in the
    database.

    Both are in pilot_6, i.e., the CURRENT_PILOT.
    '''
    @pytest.mark.django_db
    def test_command(self, email_db_setup, caplog):
        with caplog.at_level(logging.INFO):
            with patch.object(Command, '_send_email') as mock_send:
                call_command('send_emails', 
                               '--eds_email', 
                               '-a 5', 
                               '--select_pilot=pilot_6')

        self._assertion_helper(caplog)

    @pytest.mark.django_db
    def test_form(self, email_db_setup, caplog, auth_client):
        with caplog.at_level(logging.INFO):
            url = reverse('send_emails')

            response = auth_client.post(url, {
                    'action': 'eds_form', 
                    'date': 'October 31, 2018',
                    'time': '9:00 AM',
                    'select_pilot': CURRENT_PILOT 
                })

        self._assertion_helper(caplog)

    def _assertion_helper(self, caplog):
        eds_sent_applications = Application.objects.filter(eds_sent=True)
        # We started with one application where the EDS had been sent.
        # With the addition of two for Rivers and one for Karen, we
        # should see four applications where `eds_sent` = True.
        assert len(eds_sent_applications) == 4
        assert len(eds_sent_applications.filter(first_name='Rivers')) == 2
        assert len(eds_sent_applications.filter(first_name='Karen')) == 1

        lines = caplog.text.splitlines()

        # Assert Rivers and Karen received one email apiece.
        assert len(lines) == 2


class TestEdsDenialEmail:
    '''
    Test that we (1) notify applicants with all non-denied applications on Step 7,
    and (2) deny those applicants.
    '''
    applications_to_deny = []
    
    @pytest.mark.django_db
    def test_command(self, email_db_setup, caplog):
        applications = Application.objects.filter(applicationstatus__current_step_id__step=7)\
                                          .filter(applicationstatus__denied=False)\
                                          .distinct()

        # Store active applications on step 7
        self.applications_to_deny = [app.id for app in applications]

        with caplog.at_level(logging.INFO):
            with patch.object(Command, '_send_email') as mock_send:
                call_command('send_emails', 
                             '-a 5', 
                             '--select_pilot={}'.format(CURRENT_PILOT),
                             '--eds_denial_email')

        self._assertion_helper(caplog)

    def test_form(self, email_db_setup, caplog, auth_client):
        applications = Application.objects.filter(applicationstatus__current_step_id__step=7)\
                                          .filter(applicationstatus__denied=False)\
                                          .distinct()

        # Store active applications on step 7
        self.applications_to_deny = [app.id for app in applications]

        with caplog.at_level(logging.INFO):
            url = reverse('send_emails')

            response = auth_client.post(url, {
                    'action': 'eds_denial_form', 
                    'select_pilot': CURRENT_PILOT 
                })

        self._assertion_helper(caplog)

    def _assertion_helper(self, caplog):
        lines = caplog.text.splitlines()

        for app_id in self.applications_to_deny:
            app = Application.objects.get(id=app_id)

            log_count = len([line for line in lines if app.email in line])

            assert log_count == 1

            # Assert no applications remain on step 7
            assert all([status.current_step != 7 for status in app.applicationstatus_set.all()])

            # If current step is None, assert application was denied
            assert all([status.denied for status in app.applicationstatus_set.all() if not status.current_step])


class TestCustomEmail:
    parameters = [
                    ('on_step', '6', 'pilot_6', Q(current_step__step=6, application__pilot='pilot_6')),
                    ('on_step', '6', 'pilot_7', Q(current_step__step=6, application__pilot='pilot_7')),
                    ('not_on_step', '8', 'pilot_6', Q(current_step__step__in=[i for i in range(12) if i != 8],                              application__pilot='pilot_6')),
                    ('not_on_step', '8', 'pilot_7', Q(current_step__step__in=[i for i in range(12) if i != 8],                              application__pilot='pilot_7')),
                    ('on_steps_before', '8', 'pilot_6', Q(current_step__step__lt=8, application__pilot='pilot_6')),
                    ('on_steps_before', '8', 'pilot_7', Q(current_step__step__lt=8, application__pilot='pilot_7')),
                    ('on_steps_after', '6', 'pilot_6', Q(current_step__step__gt=6, application__pilot='pilot_6')),
                  ]

    @pytest.mark.parametrize('custom,step,pilot,q_filter', parameters)
    @pytest.mark.django_db
    def test_command(self, email_db_setup, caplog, custom, step, pilot, q_filter):
        base_context = {'subject': 'test email', 'email_text': 'test text'}

        with caplog.at_level(logging.INFO):
            with patch.object(Command, '_send_email') as mock_send:
                call_command('send_emails', 
                             '-a 5', 
                             '--select_pilot={}'.format(pilot),
                             custom_email=custom, 
                             steps=step, 
                             base_context=json.dumps(base_context))

        self._assertion_helper(caplog, pilot, q_filter)

    @pytest.mark.parametrize('custom,step,pilot,q_filter', parameters)
    @pytest.mark.django_db
    def test_form(self, email_db_setup, caplog, custom, step, pilot, q_filter, auth_client):
        with caplog.at_level(logging.INFO):
            url = reverse('send_emails')

            response = auth_client.post(url, {
                    'action': 'custom_form',
                    'step': step,
                    'every_status': False,
                    'selection': custom,
                    'subject': 'an email subject line',
                    'text': 'a custom email for you',
                    'select_pilot': pilot, 
                })

        self._assertion_helper(caplog, pilot, q_filter)

    def _assertion_helper(self, caplog, pilot, q_filter):
        lines = caplog.text.splitlines()


        statuses = ApplicationStatus.objects.none()

        for line in lines:
            # Parse the log entry.
            email = line.split('|')[4].strip()
            email = email

            csv_pins = line.split('|')[-1]
            pins = [int(s) for s in csv_pins.split(',')]

            statuses |= ApplicationStatus.objects.filter(application__email=email,
                                                         lot__pin__in=pins,
                                                         application__pilot=pilot)

        # Assert all statuses meet the given step criteria.
        assert statuses.count() == statuses.filter(q_filter).count()

        # Assert an email was logged for every distinct email address with a
        # qualifying status.
        assert len(lines) == Application.objects.filter(applicationstatus__in=statuses, pilot=pilot)\
                                                .distinct('email')\
                                                .count()

class TestLottoEmail:
    '''
    This test checks that the correct number of lotto emails go to the
    appropriate recipients.
    '''
    @pytest.mark.parametrize('lot_count,applicant_count,pilot', [
                                (1, 1, CURRENT_PILOT),
                                (2, 3, CURRENT_PILOT),
                                (1, 1, 'pilot_7'),
                                (2, 3, 'pilot_7'),
                            ])
    @pytest.mark.django_db
    def test_command(self, email_db_setup, lot_count, applicant_count, pilot, caplog):
        base_context = {'date': 'October 31, 2018', 'time': '9:00 AM'}

        with caplog.at_level(logging.INFO):
            with patch.object(Command, '_send_email') as mock_send:
                call_command('send_emails', 
                             '-a 5', 
                             '--lotto_email', 
                             '-n {}'.format(lot_count),
                             '-p {}'. format(pilot), 
                             base_context=json.dumps(base_context))

        self._assertion_helper(caplog, applicant_count)

    @pytest.mark.parametrize('lot_count,applicant_count,pilot', [
                                (1, 2, CURRENT_PILOT),
                                (2, 3, CURRENT_PILOT),
                                (1, 2, 'pilot_7'),
                                (2, 3, 'pilot_7'),
                            ])
    @pytest.mark.django_db
    def test_command(self, email_db_setup, auth_client, lot_count, applicant_count, pilot, caplog):
        with caplog.at_level(logging.INFO):
            url = reverse('send_emails')

            response = auth_client.post(url, {
                    'action': 'lottery_form',
                    'date': 'October 31, 2018',
                    'time': '9:00 AM', 
                    'number': lot_count,
                    'location': 'City Hall',
                    'select_pilot': pilot,                  
                })

        self._assertion_helper(caplog, applicant_count)

    def _assertion_helper(self, caplog, applicant_count):
        lotto_sent_applications = ApplicationStatus.objects.filter(lottery_email_sent=True)

        assert len(lotto_sent_applications) == applicant_count

        lines = caplog.text.splitlines()

        assert all(['October 31, 2018' in line for line in lines])
        assert len([line for line in lines if '9:00 AM' in line]) == applicant_count
