import csv
from io import StringIO

from django.urls import reverse
import pytest

from ..test_config import CURRENT_PILOT


@pytest.mark.django_db
def test_fields_in_csv(application,
                       application_status,
                       auth_client):

    application = application.build()
    application_status = application_status.build(application, step=2)

    url = reverse('csv_dump', args=[CURRENT_PILOT, 'all', 'application'])
    
    rv = auth_client.post(url)

    reader = csv.DictReader(StringIO(rv.content.decode()))
    applicants_downloaded = [row for row in reader]
    for download in applicants_downloaded:
        # Test that address info is in discrete categories and all caps.
        assert download['Owned Street Dir'].isupper()
        assert download['Owned Street Name'].isupper()
        assert download['Owned Street Type'].isupper()
        assert download['Lot Street Dir'].isupper()
        assert download['Lot Street Name'].isupper()
        assert download['Lot Street Type'].isupper()
        # Test that the CSV contains a field for PPF and EDS 
        assert 'EDS Received' in download
        assert 'PPF Received' in download

@pytest.mark.django_db
def test_owned_pin_edit(application,
                        application_status,
                        auth_client):
    application = application.build()
    application_status = application_status.build(application, step=2)
    owned_pin = application.owned_pin
    new_owned_pin = '2623330090000'

    url = reverse('review_status_log', args=[application_status.id])

    response = auth_client.post(url, {
        'owned_pin': [new_owned_pin],
        'street': [application.owned_address.street] 
    })

    application.refresh_from_db()

    assert application.owned_pin == new_owned_pin
    assert application.owned_pin != owned_pin

@pytest.mark.django_db
def test_owned_address_edit(application,
                        application_status,
                        auth_client):
    application = application.build()
    application_status = application_status.build(application, step=2)
    street = application.owned_address.street
    new_street = '25 Brook St'
    
    url = reverse('review_status_log', args=[application_status.id])

    response = auth_client.post(url, {
        'owned_pin': [application.owned_pin],
        'street': [new_street]
    })

    application.refresh_from_db()
    application.owned_address.refresh_from_db()

    assert application.owned_address.street == new_street
    assert application.owned_address.street != street
    assert application.owned_address.street_number == '25'
