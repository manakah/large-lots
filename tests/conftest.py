import datetime
import uuid

import pytest

# pytest inexplicably can't load this specific fixture, so
# import it manually. I've opened an issue for pytest here:
# https://github.com/pytest-dev/pytest-django/issues/574
from pytest_django.fixtures import db

from lots_admin.look_ups import APPLICATION_STATUS
from lots_admin.models import Address, Application, Lot, ApplicationStep, \
    ApplicationStatus

@pytest.fixture
@pytest.mark.django_db
def app_steps(db):
    order = [
        'deed',
        'location',
        'multi',
        'lottery',
        'letter',
        'EDS_waiting',
        'EDS_submission',
        'city_council',
        'debts',
        'sold',
    ]

    for idx, short_name in enumerate(order, start=1):
        spec = {
            'description': APPLICATION_STATUS[short_name],
            'step': idx,
        }
        ApplicationStep.objects.get_or_create(**spec)

@pytest.fixture
@pytest.mark.django_db
def address(db):
    address = Address.objects.create(street='a fake address', ward=2)
    return address

@pytest.fixture
@pytest.mark.django_db
def lot(db, address):
    # Create lot
    lot_info = {
        'pin': '16244240380000',
        'address': address,
    }
    lot = Lot.objects.create(**lot_info)
    return lot

@pytest.fixture
@pytest.mark.django_db
def application(db, lot, address, app_steps):
    # Create application
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
        'pilot': 'pilot_6_dev',
        'eds_sent': True,
    }

    application = Application.objects.create(**application_info)

    # Create an application status
    desc = 'Approval of EDS - Applicant submitted EDS and principal profile'
    wait_for_eds = ApplicationStep.objects.get(description=desc)

    application_status_info = {
        'denied': False,
        'application': application,
        'lot': lot,
        'current_step': wait_for_eds,
        'lottery': False,
    }

    application_status = ApplicationStatus.objects.create(**application_status_info)

    # Add the lot and the application status to the application
    application.lot_set.add(lot)
    application.status = application_status
    application.save()

    return application
