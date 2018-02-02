import pytest

from ..conftest import add_status
from lots_admin.models import ApplicationStep


@pytest.fixture
@pytest.mark.django_db
def django_db_setup(application, application_status):
    '''
    For the existing tests, we only require one application on step 7,
    so create that here using our modular fixtures.
    '''
    add_status(application, application_status, step=7)
