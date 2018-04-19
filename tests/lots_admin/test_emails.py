import pytest
from unittest.mock import patch
import sys

from django.core.management import call_command

from lots_admin.models import Application, ApplicationStatus
from lots_admin.management.commands.send_emails import Command


@pytest.mark.django_db
def test_eds_email(email_db_setup):
    '''
    Test that we appropriately select and notify Rivers Cuomo
    and Karen Oh, and update their active applications in the
    database.
    '''
    with patch.object(Command, 'send_email') as mock_send:
        call_command('send_emails', eds_email=5, stdout=sys.stdout)

    eds_sent_applications = Application.objects.filter(eds_sent=True)

    # We started with one application where the EDS had been sent.
    # With the addition of two for Rivers and one for Karen, we
    # should see four applications where `eds_sent` = True.
    assert len(eds_sent_applications) == 4
    assert len(eds_sent_applications.filter(first_name='Rivers')) == 2
    assert len(eds_sent_applications.filter(first_name='Karen')) == 1

@pytest.mark.django_db
def test_lotto_email_morning(email_db_setup):
    '''
    This test checks that the correct number of lotto emails go to the appropriate recipients.
    '''
    with patch.object(Command, 'send_email') as mock_send:
        call_command('send_emails', lotto_email='morning', lotto_offset='1', stdout=sys.stdout)

    lotto_sent_applications = ApplicationStatus.objects.filter(lottery_email_sent=True)

    # Three applicant-statuses are set for lottery.
    # The 'morning' mail, with an offset of 1, should go to two of those three.
    assert len(lotto_sent_applications) == 2
    assert len(lotto_sent_applications.filter(application__first_name='Barbara')) == 1
    assert len(lotto_sent_applications.filter(application__first_name='Nathalie')) == 1

@pytest.mark.django_db
def test_lotto_email_afternoon(email_db_setup):
    '''
    This test checks that the correct number of lotto emails go to the appropriate recipients.
    '''
    with patch.object(Command, 'send_email') as mock_send:
        call_command('send_emails', lotto_email='afternoon', lotto_offset='1', stdout=sys.stdout)

    lotto_sent_applications = ApplicationStatus.objects.filter(lottery_email_sent=True)

    # Three applicant-statuses are set for lottery.
    # The 'afternoon' mail, with an offset of 1, should go to one of those three.
    assert len(lotto_sent_applications) == 1
    assert len(lotto_sent_applications.filter(application__first_name='Barbara')) == 1

@pytest.mark.django_db
def test_closing_invitations(email_db_setup, capsys):
    with patch.object(Command, 'send_email') as mock_send:
        call_command('send_emails', closing_invitations=3, date='2017-11-13')

    # Test applications are updated
    invited = Application.objects.filter(closing_invite_sent=True)
    assert len(invited) == 3

    # Command will invite half the given number of applicants, n, rounding the
    # first group DOWN if n / 2 is not an integer. Given an n of 3, test 1
    # is invited to the morning event and 2 are invited to the afternoon event.

    out, err = capsys.readouterr()
    lines = out.splitlines()

    assert all(['2017-11-13' in line for line in lines])
    assert len([line for line in lines if '09:00' in line]) == 1
    assert len([line for line in lines if '13:00' in line]) == 2

@pytest.mark.django_db
def test_eds_denials(email_db_setup, capsys):
    applications = Application.objects.filter(applicationstatus__current_step_id__step=7)\
                                      .filter(applicationstatus__denied=False)\
                                      .distinct()

    # Store active applications on step 7
    applications_to_deny = [app.id for app in applications]

    # Assert there are, in fact, applications we need to deny
    assert len(applications_to_deny)

    with patch.object(Command, 'send_email') as mock_send:
        call_command('send_emails', eds_denial=True, separate_emails='weezerules@yahoo.com')

    log, _ = capsys.readouterr()

    for app_id in applications_to_deny:
        app = Application.objects.get(id=app_id)

        if app.email == 'weezerules@yahoo.com':
            # Assert two emails sent
            assert log.count(app.email) == 2
        else:
            # Assert one email sent
            assert log.count(app.email) == 1

        # Assert no applications remain on step 7
        assert all([status.current_step != 7 for status in app.applicationstatus_set.all()])

        # If there current step is None, assert application was denied
        assert all([status.denied for status in app.applicationstatus_set.all() if not status.current_step])
