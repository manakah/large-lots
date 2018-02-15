import pytest
import sys
import json
from urllib.parse import urlparse

from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail

from lots_admin.look_ups import DENIAL_REASONS
from lots_admin.models import Application, ApplicationStatus, Review


@pytest.mark.django_db
def test_move_to_step_9(application,
                        application_status,
                        auth_client):

    # Put our application on step 8
    app = application.build()
    app_status = application_status.build(app, step=8)

    url = reverse('bulk_submit')

    response = auth_client.post(url, {
        'step': ['step9'],
        'letter-received': [app_status.id]
    })

    # The page should redirect after form submission
    assert response.status_code == 302

    app_status.refresh_from_db()

    assert app_status.current_step.step == 9

def test_lottery_submit(application,
                        application_status,
                        auth_client):
    # Create two distinct applications to compete in lottery.
    app_cats = application.build()
    app_butterflies = application.build(last_name="Butterflies")
    app_status_cats = application_status.build(app_cats, step=6, lottery=True)
    app_status_butterflies = application_status.build(app_butterflies, step=6, lottery=True)

    # Find the PIN that both applicants requested, and post to lottery_sbumit with a winner. 
    lot = app_status_cats.lot.pin
    url = reverse('lottery_submit', args=[lot])

    response = auth_client.post(url, {
        'winner-select': app_status_butterflies.id
    })

    assert response.status_code == 302

    app_status_cats.refresh_from_db()
    app_status_butterflies.refresh_from_db()

    assert app_status_cats.denied == True
    assert app_status_cats.current_step == None

    assert app_status_butterflies.denied == False
    assert app_status_butterflies.current_step.step == 7

def test_deny_submit(application,
                     application_status,
                     auth_client):

    application = application.build()
    application_status = application_status.build(application, step=2)

    url = reverse('deny_submit', args=[application_status.id])

    response = auth_client.post(url, {
        'reason': DENIAL_REASONS['document']
    })

    assert response.status_code == 302

    application_status.refresh_from_db()
    review = Review.objects.filter(application=application_status).latest('id')

    assert application_status.denied == True
    assert application_status.current_step == None
    assert review.denial_reason.value == DENIAL_REASONS['document']

    # Test that an email with correct subject was sent.
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == 'Notification from LargeLots'

def test_deed_check_submit(application,
                           application_status,
                           auth_client):
    
    application = application.build()
    application_status = application_status.build(application, step=2)

    url = reverse('deed_check_submit', args=[application_status.id])

    # Deny the applicant because their owned property is a church.
    response = auth_client.post(url, {
        'document': 'yes',
        'name': 'on',
        'address': 'on',
        'church': 'yes'
    })

    # Check that the response redirects to the correct URL.
    assert response.status_code == 302
    assert response.url == ('/deny-application/{}/?reason=church').format(application_status.id) 