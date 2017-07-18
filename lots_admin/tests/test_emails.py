import pytest
from unittest.mock import patch
import sys

from django.core.management import call_command

from lots_admin.models import Application, ApplicationStatus
from lots_admin.management.commands.send_emails import Command

@pytest.mark.django_db
def test_eds_email(django_db_setup, capsys):
    '''The test database contains four application statuses,
    two for Rivers Cuomo on step 7 with no EDS sent, one
    for Robin Peckinold on step 6, and one for Lana Del Rey
    on step 7 with EDS already sent.

    Test that we appropriately select and notify Rivers Cuomo
    once, and update all his applications in the database.

    Expect out text from `send_emails` call is:

    Notified Rivers Cuomo - Application ID 1
    Updated applications for Rivers Cuomo - Application ID 1:
    Rivers Cuomo - Application ID 1
    Rivers Cuomo - Application ID 2
    '''

    with patch.object(Command, 'send_email') as mock_send:
        call_command('send_emails', eds_email=5, stdout=sys.stdout)
        out, err = capsys.readouterr()

    notification_message = 'Notified Rivers Cuomo - Application ID 1'
    
    applications = ['Rivers Cuomo - Application ID {}'.format(i) for i in (1, 2)]
    applications_message = '\n'.join(applications)

    for message in (notification_message, applications_message):
        assert message in out

    for applicant in ('Lana Del Rey', 'Robin Peckinold'):
        assert applicant not in out

    updated_applications = Application.objects.filter(first_name='Rivers', 
                                                      last_name='Cuomo')

    for application in updated_applications:
        assert application.eds_sent == True
        
