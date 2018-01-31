import pytest
import sys
import json

from django.urls import reverse
from django.contrib.auth.models import User

from lots_admin.models import Application, ApplicationStatus

from ..conftest import add_status


@pytest.mark.django_db
def test_move_to_step_9(application,
                        application_status,
                        auth_client):

    # Put our application on step 8
    _, app_status = add_status(application, application_status, step=8)

    url = reverse('bulk_submit')

    response = auth_client.post(url, {
        'step': ['step9'],
        'letter-received': [app_status.id]
    })

    # The page should redirect after form submission
    assert response.status_code == 302

    app_status.refresh_from_db()

    assert app_status.current_step.step == 9
