import pytest
from unittest.mock import patch
import sys

from django.core.management import call_command

from lots_admin.models import Application, ApplicationStatus
from lots_admin.management.commands.send_emails import Command

'''
The test database contains nine application statuses
for six applicants:

* Two application statuses for Rivers Cuomo, both on step 7,
  eds_sent = False
* One application statuses for Robin Peckinold on step 6
* One application statuses for Lana Del Rey on step 7, 
  eds_sent = True
* Two application statuses for Karen Oh, one denied on step 7
  and one active on step 7, eds_sent = False
* Two application statues for Barbara Hannigan, both set for lottery
* One application status for Nathalie Stutzmann, set for lottery
'''

@pytest.mark.django_db
def test_eds_email(django_db_setup):
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
def test_lotto_email_morning(django_db_setup):
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
def test_lotto_email_afternoon(django_db_setup):
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
def test_closing_invitations(django_db_setup, capsys):
    with patch.object(Command, 'send_email') as mock_send:
        call_command('send_emails', closing_invitations=3)

    # Test applications are updated
    invited = Application.objects.filter(closing_invite_sent=True)
    assert len(invited) == 3

    # Command will invite half the given number of applicants, n, rounding the
    # first group DOWN if n / 2 is not an integer. Given an n of 3, test 1
    # is invited to the morning event and 2 are invited to the afternoon event.
    out, err = capsys.readouterr()
    lines = out.splitlines()
    assert len([line for line in lines if '09:00' in line]) == 1
    assert len([line for line in lines if '13:00' in line]) == 2
