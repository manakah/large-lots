import csv
import datetime
from io import StringIO

from django.urls import reverse
import pytest

from lots_admin.models import PrincipalProfile

from ..test_config import CURRENT_PILOT


date_params = [
    None,
    datetime.datetime.now().isoformat(),
]

@pytest.mark.django_db
def test_export_ppf(principal_profile,
                    principal_profile_with_related_person,
                    auth_client):

    url = reverse('csv_dump', args=[CURRENT_PILOT, None, 'ppf'])

    rv = auth_client.post(url)

    reader = csv.DictReader(StringIO(rv.content.decode()))
    exported_profiles = [row for row in reader]
    existing_profiles = PrincipalProfile.objects\
                                        .filter(deleted_at__isnull=True)

    assert len(exported_profiles) == len(existing_profiles)

    for export, existing in zip(exported_profiles, existing_profiles):
        assert existing.entity.first_name == export['First name']
        assert existing.entity.last_name == export['Last name']
        assert existing.address == export['Home address']
        assert str(existing.date_of_birth) == export['Date of birth']
        assert existing.social_security_number == export['Social Security number']
        assert existing.drivers_license_state == export['Driver\'s license state']
        assert existing.drivers_license_number == export['Driver\'s license number']
        assert existing.license_plate_state == export['License plate state']
        assert existing.license_plate_number == export['License plate number']

    assert all(profile.exported_at for profile in existing_profiles)

@pytest.mark.django_db
@pytest.mark.parametrize('export_date', date_params)
def test_delete_enabled_appropriately(principal_profile,
                                      auth_client,
                                      export_date):

    principal_profile.exported_at = export_date
    principal_profile.save()

    rv = auth_client.get('/principal-profiles/')

    warning = 'You must export all PPFs before you can delete them!'

    if export_date:
        assert not warning in rv.content.decode()
    else:
        assert warning in rv.content.decode()

@pytest.mark.django_db
@pytest.mark.parametrize('export_date', date_params)
def test_delete_ppf(principal_profile, auth_client, export_date):
    '''
    Test that principal profiles that have not been exported, are not
    deleted; and principal profiles that have been exported, are.
    '''

    principal_profile.exported_at = export_date
    principal_profile.save()

    url = reverse('delete_principal_profiles', args=[CURRENT_PILOT])
    rv = auth_client.post(url)

    principal_profile.refresh_from_db()

    for field in ('date_of_birth',
                  'social_security_number',
                  'drivers_license_state',
                  'drivers_license_number',
                  'license_plate_state',
                  'license_plate_number'):

        data = getattr(principal_profile, field)

        if export_date:
            assert not data

        else:
            assert data

    if export_date:
        assert principal_profile.deleted_at

    else:
        assert not principal_profile.deleted_at
