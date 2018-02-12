import pytest

from django.core.urlresolvers import reverse


@pytest.mark.django_db
def test_eds_submission(application, client):
    app = application.build()
    data = {'tracking_id': app.tracking_id}
    response = client.post(reverse('eds_submission'), data=data)

    assert response.status_code == 200

    app.refresh_from_db()

    assert app.eds_received == True
