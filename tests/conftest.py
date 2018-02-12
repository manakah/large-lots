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
    order = [
        'deed',
        'location',
        'multi',
        'letter',
        'lottery',
        'EDS_waiting',
        'EDS_submission',
        'city_council',
        'debts',
        'sold',
    ]

    for idx, short_name in enumerate(order, start=2):
        spec = {
            'description': APPLICATION_STATUS[short_name],
            'step': idx,
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
    address = Address.objects.create(street='5000 S ELIZABETH ST', zip_code='60609', ward=2)

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

            for attribute, value in kwargs.items():
                application_info[attribute] = value

            application = Application.objects.create(**application_info)
            application.save()

            return application

    return ApplicationFactory()

@pytest.fixture
@pytest.mark.django_db
def application_status(db, lot, app_steps):
    class ApplicationStatusFactory():
        def build(self, application, step, **kwargs):
            application_status_info = {
                'denied': False,
                'lot': lot,
                'lottery': False,
            }

            for attribute, value in kwargs.items():
                application_status_info[attribute] = value

            app_status = ApplicationStatus.objects.create(**application_status_info)
            app_step = ApplicationStep.objects.get(step=step)

            app_status.current_step = app_step
            app_status.application = application
            app_status.save()

            application.lot_set.add(app_status.lot)
            application.save()

            return application, app_status

    return ApplicationStatusFactory()