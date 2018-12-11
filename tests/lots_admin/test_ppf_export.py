import csv
import datetime
from io import StringIO

from django.urls import reverse
import pytest

from lots_admin.models import PrincipalProfile, Address

from ..test_config import CURRENT_PILOT


date_params = [
    None,
    datetime.datetime.now().isoformat(),
]

@pytest.mark.django_db
def test_export_ppf(application,
                    principal_profile,
                    related_person,
                    auth_client):

    # Make a regular application & PPF
    standard_applicant = application.build()
    principal_profile.build(standard_applicant)

    # Add a related person & PPF
    principal_profile.build(standard_applicant, related_person=related_person)

    # Make an application & PPF on behalf of an organization
    organization_applicant = application.build(organization_confirmed=True,
                                               organization='Groundhog, Inc.')

    address = Address.objects.create(street='343 Underground Way',
                                     zip_code='60609',
                                     ward=3)

    principal_profile.build(organization_applicant,
                            org_applicant_address=address)

    url = reverse('csv_dump', args=[CURRENT_PILOT, None, 'ppf'])

    rv = auth_client.post(url)

    reader = csv.DictReader(StringIO(rv.content.decode()))
    exported_profiles = [row for row in reader]
    existing_profiles = PrincipalProfile.objects\
                                        .filter(deleted_at__isnull=True)

    assert len(existing_profiles) == 3
    assert len(exported_profiles) == len(existing_profiles)

    for export, existing in zip(exported_profiles, existing_profiles):
        assert ('{0} {1}').format(existing.entity.first_name, existing.entity.last_name) == export['Principal\'s Name']
        assert ('{0} {1}').format(existing.drivers_license_state, existing.drivers_license_number) == export['Driver\'s License Number']
        assert ('{0} {1}').format(existing.license_plate_state, existing.license_plate_number) == export['Plate Number']
        assert existing.social_security_number == export['Social Security Number']

        # Address is a property of the PPF model that returns the appropriate
        # address information for individual applicants, related persons,
        # and applicants applying on behalf of an organization.
        assert existing.address == export['Principal\'s Address']

        if existing.application.organization_confirmed:
            assert existing.application.organization == export['Entity']
            assert existing.application.contact_address.street == export['Address']

    assert all(profile.exported_at for profile in existing_profiles)

@pytest.mark.django_db
@pytest.mark.parametrize('export_date', date_params)
def test_delete_enabled_appropriately(application,
                                      principal_profile,
                                      auth_client,
                                      export_date):

    principal_profile.build(application.build(),
                            exported_at=export_date)

    rv = auth_client.get('/principal-profiles/')

    warning = 'You must export all PPFs before you can delete them!'

    if export_date:
        assert not warning in rv.content.decode()
    else:
        assert warning in rv.content.decode()

@pytest.mark.django_db
@pytest.mark.parametrize('export_date', date_params)
def test_delete_ppf(application,
                    principal_profile,
                    auth_client,
                    export_date):
    '''
    Test that principal profiles that have not been exported, are not
    deleted; and principal profiles that have been exported, are.
    '''
    profile = principal_profile.build(application.build(),
                                      exported_at=export_date)

    url = reverse('delete_principal_profiles', args=[CURRENT_PILOT])
    rv = auth_client.post(url)

    profile.refresh_from_db()

    for field in ('date_of_birth',
                  'social_security_number',
                  'drivers_license_state',
                  'drivers_license_number',
                  'license_plate_state',
                  'license_plate_number'):

        data = getattr(profile, field)

        if export_date:
            assert not data

        else:
            assert data

    if export_date:
        assert profile.deleted_at

    else:
        assert not profile.deleted_at
