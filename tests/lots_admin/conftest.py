import pytest

from django.core.management import call_command


@pytest.fixture
@pytest.mark.django_db(transaction=True)
def django_db_setup(django_db_setup, transactional_db):
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
    '''
    call_command('loaddata', 'tests/lots_admin/test_data.json')