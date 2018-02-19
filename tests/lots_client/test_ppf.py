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
@pytest.mark.parametrize('ppf_type', ['individual', 'organization'])
def test_individual_ppf_submission(django_db_setup,
                                   client,
                                   application,
                                   ppf_blob,
                                   ppf_type):

    if ppf_type == 'individual':
        app = application.build()
        data = ppf_blob.build(app)

    elif ppf_type == 'organization':
        app = application.build(organization_confirmed=True,
                                organization='The Peacock Company')

        data = ppf_blob.build(app, home_address='456 Feather Lane')

    rv = client.post(
        '/principal-profile-form/{}/'.format(app.tracking_id),
        data=data,
    )

    assert rv.status_code == 200
    assert 'Success!' in str(rv.content)

    app.refresh_from_db()
    assert app.ppf_received == True

    principal_profiles = app.principalprofile_set.all()
    assert len(principal_profiles) == 2

    primary_ppf = principal_profiles.first()

    if ppf_type == 'organization':
        assert primary_ppf.address == '456 Feather Lane'

    elif ppf_type == 'individual':
        assert primary_ppf.address == app.contact_address.street

    related_person = app.relatedperson_set.get()
    related_ppf = principal_profiles.last()

    assert 'Petmore Dogs' in str(related_person)
    assert related_ppf.address == related_person.address.street
