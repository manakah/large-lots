import pytest
from pytest_django.fixtures import db

from django.core.management import call_command

from lots_admin.models import PrincipalProfile, RelatedPerson


@pytest.fixture
@pytest.mark.django_db(transaction=True)
def email_db_setup(django_db_setup, transactional_db):
    '''
    The test database contains nine application statuses
    for six applicants:

    * Two application statuses for Rivers Cuomo, both on step 7,
      eds_sent = False
    * One application statuses for Robin Peckinold on step 6
    * One application statuses for Lana Del Rey on step 7,
      eds_sent = True
    * Two application statuses for Karen Oh, one denied on step 7
      and one active on step 7, eds_sent = False
    * Two application statues for Barbara Hannigan, both set for lottery
    * One application status for Nathalie Stutzmann, set for lottery

    This fixture will be deprecated when we implement the email interface
    in lieu of more modular, easier to follow fixtures.
    '''
    call_command('loaddata', 'tests/lots_admin/test_data.json')

@pytest.fixture
@pytest.mark.django_db
def principal_profile(application, db):
    data = {
        'application': application,
        'date_of_birth': '1992-02-16',
        'social_security_number': '123-45-6789',
        'drivers_license_state': 'IL',
        'drivers_license_number': 'foo',
        'license_plate_state': 'NA',
    }

    ppf = PrincipalProfile.objects.create(**data)

    return ppf

@pytest.fixture
@pytest.mark.django_db
def related_person(application, address, db):
    data = {
        'application': application,
        'first_name': 'Austin',
        'last_name': 'Powers',
        'address': address,
    }

    related_person = RelatedPerson.objects.create(**data)

    return related_person

@pytest.fixture
@pytest.mark.django_db
def principal_profile_with_related_person(application, related_person, db):
    data = {
        'application': application,
        'related_person': related_person,
        'date_of_birth': '1992-02-16',
        'social_security_number': '123-45-6789',
        'drivers_license_state': 'IL',
        'drivers_license_number': 'foo',
        'license_plate_state': 'NA',
    }

    ppf = PrincipalProfile.objects.create(**data)

    return ppf
