import csv

from django.urls import reverse
import pytest

from ..test_config import CURRENT_PILOT


@pytest.mark.django_db
def test_export_ppf(principal_profile,
                    principal_profile_with_related_person,
                    auth_client):

    url = reverse('csv_dump', args=[CURRENT_PILOT, None, 'ppf'])

    rv = auth_client.post(url)

    # parse csv content
