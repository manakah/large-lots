import datetime
import uuid

import pytest

# pytest inexplicably can't load this specific fixture, so
# import it manually. I've opened an issue for pytest here:
# https://github.com/pytest-dev/pytest-django/issues/574
from pytest_django.fixtures import db

from lots_admin.look_ups import APPLICATION_STATUS
from lots_admin.models import Address, Application, Lot, ApplicationStep, \
    ApplicationStatus, User

from .test_config import CURRENT_PILOT


@pytest.fixture
@pytest.mark.django_db
def app_steps(db):
    # Every step has a public status of valid, except step 2, which has a
    # public status of approved. Make this dict so we can `get` the correct
    # status for step 2, and fallback to valid for the rest.
    public_status = {2: 'approved'}

    for idx, description in enumerate(APPLICATION_STATUS.values(), start=2):
        spec = {
            'description': description,
            'step': idx,
            'public_status': public_status.get(idx, 'valid'),
        }
        ApplicationStep.objects.create(**spec)

@pytest.fixture
@pytest.mark.django_db
def auth_client(db, client):
    User.objects.create_user(username='user', password='password')
    client.login(username='user', password='password')
    return client

@pytest.fixture
@pytest.mark.django_db
def address(db):
    address_info = {
        'street': '5000 S ELIZABETH ST',
        'street_number': '5000',
        'street_dir': 'S',
        'street_name': 'ELIZABETH',
        'street_type': 'ST',
        'zip_code': '60609',
        'ward': 2
    }

    address = Address.objects.create(**address_info)

    return address

@pytest.fixture
@pytest.mark.django_db
def lot(db, address):
    lot_info = {
        'pin': '16244240380000',
        'address': address,
    }
    lot = Lot.objects.create(**lot_info)
    return lot

@pytest.fixture
@pytest.mark.django_db
def application(db, address):
    class ApplicationFactory():
        def build(self, **kwargs):
            application_info = {
                'first_name': 'Seymour',
                'last_name': 'Cats',
                'organization': '',
                'owned_pin': '16133300170000',
                'owned_address': address,
                'deed_image': 'a-deed-image.png',
                'deed_timestamp': datetime.datetime.now(),
                'contact_address': address,
                'phone': '555-555-5555',
                'email': 'testing+{}@datamade.us'.format(uuid.uuid4()),
                'how_heard': '',
                'tracking_id': uuid.uuid4(),
                'received_date': datetime.datetime.now(),
                'pilot': CURRENT_PILOT,
            }

            application_info.update(kwargs)

            application = Application.objects.create(**application_info)
            application.save()

            return application

    return ApplicationFactory()

@pytest.fixture
@pytest.mark.django_db
def application_status(db, lot, app_steps):
    class ApplicationStatusFactory():
        '''
        This class adds creates an ApplicationStatus with related Application.

        The build function accepts an instance of an Application, a specified step, and 
        other model fields as needed: lottery, lottery_email_sent, denied, etc.
        '''
        def build(self, application, step, **kwargs):
            app_step = ApplicationStep.objects.get(step=step)

            application_status_info = {
                'denied': False,
                'lot': lot,
                'lottery': False,
                'application_id': application.id,
                'current_step_id': app_step.id,
                'is_resident': True,
            }

            application_status_info.update(kwargs)

            app_status = ApplicationStatus.objects.create(**application_status_info)

            application.lot_set.add(app_status.lot)
            application.save()

            return app_status

    return ApplicationStatusFactory()