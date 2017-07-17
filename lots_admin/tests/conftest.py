import pytest

from django.core.management import call_command

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    '''Insert the following into the test_largelots database:

    * Two addresses
      * 1 - 4539 N Paulina
      * 2 - 440 S LaSalle

    * Two lots
      * 13131 - corresponds to address 1
      * 34343 - corresponds to address 2

    * Two application steps
      * 1 - Step 6: Alderman letter
      * 2 - Step 7: EDS needed

    * Three applications
      * 1 - Rivers Cuomo
      * 2 - Robin Peckinold
      * 3 - Lana Del Rey

    * Three application statuses
      * 1 - Rivers Cuomo, EDS needed, not sent (13131)
      * 2 - Rivers Cuomo, EDS needed, not sent (34343)
      * 3 - Robin Peckinold, Alderman letter (34343)
      * 4 - Lana Del Rey, EDS needed and sent (34343)
    '''
    with django_db_blocker.unblock():
        call_command('loaddata', 'tests/test_data.json')