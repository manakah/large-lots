import pytest


@pytest.fixture
@pytest.mark.django_db
def django_db_setup(application):
    pass
