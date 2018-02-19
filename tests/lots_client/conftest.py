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

@pytest.fixture
def ppf_blob():
    class PPFBlobFactory():

        def build(self, app, **kwargs):
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

            safe_kwargs = {}

            for k, v in kwargs.items():
                safe_kwargs['form-0-{}'.format(k)] = v

            data.update(safe_kwargs)

            return data

    return PPFBlobFactory()
