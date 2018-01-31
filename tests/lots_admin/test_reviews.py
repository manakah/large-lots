import pytest
import sys
import json

from django.urls import reverse
from django.contrib.auth.models import User

from lots_admin.models import Application, ApplicationStatus


@pytest.mark.django_db
def test_move_to_step_9(email_db_setup, client):
    '''
    This test checks that the reviewer moved an applicant from step 8 to step 9.
    '''
    # Create user to fulfill @login_required (can't use pytest-django's
    # admin_user fixture because the password is not hashed, so login
    # doesn't work)
    User.objects.create_user(username='user', password='password')
    client.login(username='user', password='password')

    applicant = ApplicationStatus.objects.filter(current_step__step=8).first()
    assert applicant.current_step.step == 8

    url = reverse('bulk_submit')
    response = client.post(url, {'step': ['step9'], 'letter-received': ['10']})

    # The page should redirect after form submission
    assert response.status_code == 302

    applicant.refresh_from_db()

    assert applicant.current_step.step == 9
