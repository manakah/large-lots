import pytest
from unittest.mock import patch
import sys

from django.core.management import call_command

from lots_admin.models import Application, ApplicationStatus
from lots_admin.management.commands.send_emails import Command

@pytest.mark.django_db
def test_eds_email(django_db_setup):
    '''The test database contains six application statuses
    for four applicants:

    * Two applications for Rivers Cuomo, both on step 7,
      eds_sent = False
    * One application for Robin Peckinold on step 6
    * One application for Lana Del Rey on step 7, 
      eds_sent = True
    * Two applications for Karen Oh, one denied on step 7
      and one active on step 7, eds_sent = False

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

