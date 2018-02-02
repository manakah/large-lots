import pytest

from django.core.urlresolvers import reverse


@pytest.mark.django_db
def test_eds_submission(application, client):
    data = {'tracking_id': application.tracking_id}
    response = client.post(reverse('eds_submission'), data=data)

    assert response.status_code == 200

    application.refresh_from_db()

    assert application.eds_received == True
