import json

import pytest

from lots_admin.models import Application, LotUse
from ..test_config import CURRENT_PILOT


@pytest.mark.django_db
@pytest.mark.parametrize('organization,organization_confirmed', [
    (None, False),
    ('Eighth Blackbird', True),
    (None, True)
])
def test_organization_field(django_db_setup,
                            client,
                            mock_file,
                            application_blob,
                            organization,
                            organization_confirmed):
    '''
    Tests that the application:
    (1) validates without organization and organization_confirmed.
    (2) validates with organization and organization_confirmed.
    (3) does not validate without organization but with organization_confirmed.
    '''
    app_data = application_blob

    if organization:
        app_data['organization'] = organization
    if organization_confirmed:
        app_data['organization_confirmed'] = organization_confirmed

    rv = client.post('/apply/', data=app_data, files={"file": mock_file})

    new_application = Application.objects.filter(first_name="Seymour", last_name="Gerbils")

    if not organization and organization_confirmed:
        assert rv.status_code == 200
        assert "Check the box and enter an organization name, or leave both blank" in str(rv.content)
        assert not new_application
    else:
        assert rv.status_code == 302
        assert new_application

@pytest.mark.django_db
@pytest.mark.parametrize('lot_2_pin,lot_2_address', [
    ('26233300420000', '123 Main St.'),
    ('26233300420000', ''),
])
def test_lot_2_address_field(django_db_setup,
                            client,
                            mock_file,
                            lot_2_pin,
                            lot_2_address,
                            application_blob):
    '''
    Tests that the application:
    (1) validates with a lot_2_pin and address.
    (2) does not validate with a lot_2_pin without an address.
    '''
    app_data = application_blob

    lot_2_data = { 
        'lot_2_pin': lot_2_pin,
        'lot_2_address': lot_2_address,
        'lot_2_use': 'Network of climbing tunnels',
    }

    app_data.update(lot_2_data)

    rv = client.post('/apply/', data=app_data, files={"file": mock_file})

    new_application = Application.objects.filter(first_name="Seymour", last_name="Gerbils")

    if lot_2_pin and not lot_2_address:
        assert rv.status_code == 200
        assert "Please provide an address" in str(rv.content)
        assert not new_application
    else:
        assert rv.status_code == 302
        assert new_application

@pytest.mark.django_db
@pytest.mark.parametrize('lot_2', [False, True])
def test_application(application_blob,
                     address,
                     client,
                     mock_file,
                     mocker,
                     lot_2):

    mocker.patch('lots_client.views.get_ward', return_value='2')
    mocker.patch('lots_client.views.get_community', return_value='Englewood')

    app_data = application_blob

    if lot_2:
        app_data.update({
            'lot_2_address': address,
            'lot_2_pin': '16023030260000',
            'lot_2_use': 'Cover the place in sawdust',
        })

    rv = client.post('/apply/', data=app_data, files={"file": mock_file})

    assert rv.status_code == 302  # redirect to apply-confirm

    application = Application.objects.filter(last_name='Gerbils').first()

    lot_uses = LotUse.objects.filter(application=application.id)

    if lot_2:
        assert len(lot_uses) == 2
    else:
        assert len(lot_uses) == 1

    for idx, use in enumerate(lot_uses, start=1):
        pin = app_data['lot_{}_pin'.format(idx)]
        lot, = lot_uses.filter(lot__pin=pin)
        planned_use = app_data['lot_{}_use'.format(idx)]

        assert lot.planned_use == planned_use


@pytest.mark.django_db
def test_get_application_endpoint(django_db_setup, client):

    application = Application.objects.first()
    email = application.email

    rv = client.get('/api/get-applications?email={}'.format(email))

    found_applications = json.loads(rv.json())

    assert len(found_applications) == 1
    assert found_applications[0]['id'] == application.id
