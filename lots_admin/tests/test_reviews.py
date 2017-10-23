import pytest
import sys
import json

from django.urls import reverse
from django.contrib.auth.models import User

from lots_admin.models import Application, ApplicationStatus

@pytest.mark.django_db
def test_move_to_step_9(django_db_setup, client):
    '''
    This test checks that the reviewer moved an applicant from step 8 to step 9.
    '''
    # Create user to fulfill @login_required
    User.objects.create_user(username='user', password='password')
    client.login(username='user', password='password')
    # Find applicant on step 8.
    applicant_on_step_8 = ApplicationStatus.objects.get(id=10)
    assert applicant_on_step_8.current_step.step == 8
    # Send data: step selected and application status id.
    url = reverse('bulk_submit')
    response = client.post(url, {'step': ['step9'], 'letter-received': ['10']}) 
    applicant_on_step_9 = ApplicationStatus.objects.get(id=10)
    assert applicant_on_step_9.current_step.step == 9
    # The page should redirect after form submission
    assert response.status_code == 302
    