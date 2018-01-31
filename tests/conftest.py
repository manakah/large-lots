import pytest

from lots_admin.look_ups import APPLICATION_STATUS
from lots_admin.models import ApplicationStep


@pytest.fixture
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
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