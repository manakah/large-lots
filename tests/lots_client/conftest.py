import datetime
import uuid

import pytest

# pytest inexplicably can't load this specific fixture, so
# import it manually. I've opened an issue for pytest here:
# https://github.com/pytest-dev/pytest-django/issues/574
from pytest_django.fixtures import db

from lots_admin.models import Address, Application, Lot, ApplicationStep, \
    ApplicationStatus


@pytest.fixture
@pytest.mark.django_db
def django_db_setup(django_db_setup, db):
    # Create addresses
    for i in range(2):
        address = Address.objects.create(street='a fake address', ward=2)

    # Create lot
    lot_info = {
        'pin': '16244240380000',
        'address': Address.objects.first(),
    }
    lot = Lot.objects.create(**lot_info)

    # Create application
    application_info = {
        'first_name': 'Seymour',
        'last_name': 'Cats',
        'organization': '',
        'owned_pin': '16133300170000',
        'owned_address': Address.objects.last(),
        'deed_image': 'a-deed-image.png',
        'deed_timestamp': datetime.datetime.now(),
        'contact_address': Address.objects.last(),
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
    wait_for_eds = ApplicationStep.objects.get(step=7)

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

@pytest.fixture
def application(django_db_setup):
    return Application.objects.first()
