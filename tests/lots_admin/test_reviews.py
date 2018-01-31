import pytest
import sys
import json

from django.urls import reverse
from django.contrib.auth.models import User

from lots_admin.models import Application, ApplicationStatus

from ..conftest import add_status


@pytest.mark.django_db
def test_move_to_step_9(client,
                        application,
                        application_status):

    # Create user to fulfill @login_required (can't use pytest-django's
    # admin_user fixture because the password is not hashed, so login
    # doesn't work)
    User.objects.create_user(username='user', password='password')
    client.login(username='user', password='password')

    # Put our application on step 8
    _, app_status = add_status(application, application_status, step=8)

    url = reverse('bulk_submit')

    response = client.post(url, {
        'step': ['step9'],
        'letter-received': [app_status.id]
    })

    # The page should redirect after form submission
    assert response.status_code == 302

    app_status.refresh_from_db()

    assert app_status.current_step.step == 9
