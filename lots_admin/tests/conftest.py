import pytest

from django.core.management import call_command

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    '''Insert test_data.json into the `test_largelots` database,
    resulting in the following field of applicants: 

    first_name | last_name  | step | denied | eds_sent | lottery_email_sent
    ------------+------------+------+--------+----------+--------------------
     Karen      | Oh         |    5 | t      | f        | f
     Robin      | Peckinold  |    5 | f      | f        | f
     Barbara    | Hannigan   |    6 | f      | f        | f
     Barbara    | Hannigan   |    6 | f      | f        | f
     Nathalie   | Stutzmann. |    6 | f      | f        | f
     Rivers     | Cuomo      |    7 | f      | f        | f
     Rivers     | Cuomo      |    7 | f      | f        | f
     Lana       | Del Rey    |    7 | f      | t        | f
     Karen      | Oh         |    7 | f      | f        | f
    '''
    with django_db_blocker.unblock():
        call_command('loaddata', 'lots_admin/tests/test_data.json')