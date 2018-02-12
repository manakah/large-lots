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

def test_lottery_submit(application_thing,
                        application_status_thing,
                        auth_client):
    # Create two distinct applications to compete in lottery.
    application_cats = application_thing.build()
    application_butterflies = application_thing.build(last_name="Butterflies")
    _, app_status_cats = application_status_thing.build(application_cats, step=6, lottery=True)
    _, app_status_butterflies = application_status_thing.build(application_butterflies, step=6, lottery=True)

    # Find the PIN that both applicants requested, and post to lottery_sbumit with a winner. 
    lot = app_status_cats.lot.pin
    url = reverse('lottery_submit', args=[lot])

    auth_client.post(url, {
        'winner-select': app_status_butterflies.id
        })

    app_status_cats.refresh_from_db()
    app_status_butterflies.refresh_from_db()

    assert app_status_cats.denied == True
    assert app_status_cats.current_step == None

    assert app_status_butterflies.denied == False
    assert app_status_butterflies.current_step.step == 7







