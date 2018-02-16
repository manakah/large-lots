import pytest
import sys
import json
from urllib.parse import urlparse

from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail

from lots_admin.look_ups import DENIAL_REASONS
from lots_admin.models import Application, ApplicationStatus, Review


@pytest.mark.parametrize('step,lottery', [
    (5, False),
    (5, True),
    (7, False),
    (8, False),
    (9, False),
    (10, False),
])
@pytest.mark.django_db
def test_bulk_submit(application,
                     application_status,
                     auth_client,
                     step,
                     lottery):

    app = application.build()
    app_status = application_status.build(app, step=step, lottery=lottery)

    url = reverse('bulk_submit')

    # Steps 2 through 8 are "future" actions, so an applicant who is moved
    # to step 3 has completed their current step, step 2. By contrast, steps 9
    # through 11 are "past" actions, meaning an applicant who is moved from
    # step 8 to step 9 has completed step 9.

    if step in (5, 7):
        completed_step = step
    else:
        completed_step = step + 1

    response = auth_client.post(url, {
        'step': ['step{}'.format(completed_step)],
        'selected-for-bulk-submit': [app_status.id]
    })

    # The page should redirect after form submission.
    assert response.status_code == 302

    app_status.refresh_from_db()

    if step == 7:  # Check EDS flag was toggled.
        assert app_status.application.eds_received == True

    if step == 5 and not lottery:
        # Skip the lottery step and proceed to EDS.
        expected_step = step + 2
    else:
        # Go to the next step.
        expected_step = step + 1

    assert app_status.current_step.step == expected_step

    reviews = Review.objects.filter(application=app_status.id)

    assert len(reviews) == 1
    assert reviews.first().step_completed == completed_step

def test_run_lottery(application,
                     application_status,
                     auth_client):
    # Create two distinct applications to compete in lottery.
    app_cats = application.build()
    app_butterflies = application.build(last_name="Butterflies")
    app_status_cats = application_status.build(app_cats, step=6, lottery=True)
    app_status_butterflies = application_status.build(app_butterflies, step=6, lottery=True)

    # Find the PIN that both applicants requested, and post to lottery_submit with a winner.
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

def test_step_4_to_5_automation(application,
                                application_status,
                                auth_client):
    
    application_to_advance = application.build(last_name='Flamingos')
    application_to_advance_status = application_status.build(application_to_advance, step=4)

    application_to_deny = application.build(last_name='Manatees')
    application_to_deny_status = application_status.build(application_to_deny, step=3)

    url = reverse('deny_submit', args=[application_to_deny_status.id])

    response = auth_client.post(url, {
        'reason': DENIAL_REASONS['block']
    })

    application_to_advance_status.refresh_from_db()
    review = Review.objects.filter(application=application_to_advance_status).latest('id')
    # Test that Seymour Flamingos advanced to Step 5 as a side effect of denying his competitor.
    assert application_to_advance_status.denied == False
    assert application_to_advance_status.current_step.step == 5
    assert review.step_completed == 4