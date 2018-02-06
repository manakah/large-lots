import pytest
import mock

from django.core.files import File

from lots_admin.models import Application
from ..test_config import CURRENT_PILOT

@pytest.mark.django_db
@pytest.mark.parametrize('organization, organization_confirmed',[
    (None, False),
    ('Eighth Blackbird', True),
    (None, True)
    ])
def test_organization_field(django_db_setup,
                            client,
                            mocker,
                            address, 
                            organization, 
                            organization_confirmed):
    '''
    Tests that the application:
    (1) validates without organization and organization_confirmed.
    (2) validates with organization and organization_confirmed.
    (3) does not validate without organization but with organization_confirmed.
    '''

    deed_mock = mock.MagicMock(spec=File)
    deed_mock.name = 'fake_deed.jpg'

    print(address)
    
    app_data = {
        'first_name': 'Seymour',
        'last_name': 'Gerbils',
        'contact_address': '5555',
        'contact_street': 'S HERMITAGE AVE',
        'contact_city': 'Chicago',
        'contact_state': 'IL',
        'contact_zip_code': '12345',
        'email': 'seymour@datamade.us',
        'phone': '111-111-1111',
        'owned_pin': '16133300190000',
        'owned_address': address,
        'lot_1_address': address,
        'lot_1_pin': '16133300210000',
        'how_heard': '',
        'deed_image': deed_mock,
        'terms': True, 
    }

    # Sneak by image validator by mocking the results. 
    mocker.patch('lots_client.views.ApplicationForm.clean_deed_image', return_value=deed_mock.name)

    if organization:
        app_data['organization'] = organization
    if organization_confirmed:
        app_data['organization_confirmed'] = organization_confirmed

    rv = client.post('/apply/', data=app_data, files={"file": deed_mock})
    new_application = Application.objects.filter(first_name="Seymour", last_name="Gerbils")

    if not organization and organization_confirmed:
        assert rv.status_code == 200
        assert "Check the box and enter an organization name, or leave both blank" in str(rv.content)
        assert len(new_application) == 0
    else:
        assert rv.status_code == 302
        assert len(new_application) == 1
