from django.core.files import File
import pytest

from lots_admin.models import ApplicationStep


@pytest.fixture
@pytest.mark.django_db
def django_db_setup(application, application_status):
    '''
    For the existing tests, we only require one application on step 7,
    so create that here using our modular fixtures.
    '''
    app = application.build()
    application_status.build(app, step=7)

@pytest.fixture
def mock_file(mocker):
    mock_file = mocker.MagicMock(spec=File)
    mock_file.name = 'fake_deed.jpg'
    return mock_file

@pytest.fixture
def application_blob(address, mock_file, mocker):
    '''
    Patch the pesky deed validator on the ApplicationForm and return
    a dictionary of fake application data for use in tests
    '''
    mocker.patch('lots_client.views.ApplicationForm.clean_deed_image',
                 return_value=mock_file.name)

    return {
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
        'lot_1_use': 'Giant hampster wheel',
        'how_heard': '',
        'deed_image': mock_file,
        'terms': True,
    }
