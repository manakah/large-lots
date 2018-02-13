import datetime
import uuid

import pytest

from lots_admin.models import Application
from lots_client.views import advance_if_ppf_and_eds_submitted


@pytest.mark.django_db
@pytest.mark.parametrize('eds_received,ppf_received', [
    (False, False),
    (True, False),
    (False, True),
    (True, True)
])
def test_advance_to_step_8(django_db_setup,
                           eds_received,
                           ppf_received):
    
    application = Application.objects.get(applicationstatus__current_step__step=7)
    application.eds_sent = True
    application.save()

    setattr(application, 'eds_received', eds_received)
    setattr(application, 'ppf_received', ppf_received)

    if all([eds_received, ppf_received]):
        step = 8
    else:
        step = 7

    advance_if_ppf_and_eds_submitted(application)

    assert application.applicationstatus_set.first().current_step.step == step

@pytest.mark.django_db
def test_view_requires_tracking_id(django_db_setup,
                                   client,
                                   application):

    rv = client.get('/principal-profile-form/')

    assert 'Oops!' in str(rv.content)

    app = application.build()
    rv = client.get('/principal-profile-form/{}/'.format(app.tracking_id))

    assert 'Instructions' in str(rv.content)

@pytest.mark.django_db
def test_ppf_submission(django_db_setup,
                        client,
                        application):
    app = application.build()

    data = {
        'form-TOTAL_FORMS': 2,
        'form-INITIAL_FORMS': 0,
        'form-0-first_name': app.first_name,
        'form-0-last_name': app.last_name,
        'form-0-home_address': app.owned_address.street,
        'form-0-date_of_birth': '1992-02-16',
        'form-0-social_security_number': '123-45-6789',
        'form-0-drivers_license_state': 'IL',
        'form-0-drivers_license_number': 'foo',
        'form-0-license_plate_state': 'NA',
        'form-1-first_name': 'Petmore',
        'form-1-last_name': 'Dogs',
        'form-1-home_address': '4539 N Paulina St',
        'form-1-date_of_birth': '1985-05-05',
        'form-1-social_security_number': '453-21-6789',
        'form-1-drivers_license_state': 'IL',
        'form-1-drivers_license_number': 'bar',
        'form-1-license_plate_state': 'TN',
        'form-1-license_plate_number': 'baz',
    }

    rv = client.post(
        '/principal-profile-form/{}/'.format(app.tracking_id),
        data=data,
    )

    assert rv.status_code == 200
    assert 'Success!' in str(rv.content)

    app.refresh_from_db()

    related_people = app.relatedperson_set.all()

    assert app.ppf_received == True
    assert len(app.principalprofile_set.all()) == 2
    assert len(related_people) == 1
    assert 'Petmore Dogs' in str(related_people.first())
