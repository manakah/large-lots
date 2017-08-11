import pytest

from django.core.management import call_command

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    '''Insert test_data.json into the `test_largelots` database,
    resulting in the following field of applicants: 

     first_name | last_name |            email            | eds_sent | step | denied
    ------------+-----------+-----------------------------+----------+------+--------
     Rivers     | Cuomo     | weezerules@yahoo.com        | f        |    7 | f
     Rivers     | Cuomo     | weezerules@yahoo.com        | f        |    7 | f
     Robin      | Peckinold | fleetfoxesfanclub@yahoo.com | f        |    6 | f
     Lana       | Del Rey   | natlanthemmm@gmail.com      | t        |    7 | f
     Karen      | Oh        | goldlion@hotmail.com        | f        |    6 | t
     Karen      | Oh        | goldlion@hotmail.com        | f        |    7 | f
    '''
    with django_db_blocker.unblock():
        call_command('loaddata', 'lots_admin/tests/test_data.json')