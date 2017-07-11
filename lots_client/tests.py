import json

from uuid import uuid4

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings

from lots_admin.models import Address, Application, Lot, ApplicationStep, ApplicationStatus
from lots_admin.look_ups import APPLICATION_STATUS
from django.test.utils import override_settings

@override_settings(STATICFILES_STORAGE = None)
class EDSSubmissionTest(TestCase):
    def setUp(self):
        address = Address.objects.create(street='123 Main St')
        lot = Lot.objects.create(pin='16244230380000', address=address)

        app_info = {
        'first_name': 'Nico',
        'last_name': 'Muhly',
        'organization': '',
        'owned_address': address,
        'owned_pin': '16133300190000',
        'deed_image': 'pilot_6_dev/deeds/Buzz-Aldrin-1494451611_college-matching-diagram.pdf',
        'contact_address': address,
        'phone': '999-999-9999',
        'email': 'reginafcompton@datamade.us',
        'how_heard': '',
        'tracking_id': str(uuid4()),
        'pilot': settings.CURRENT_PILOT,
        }

        self.test_app = Application.objects.create(**app_info)

        # Create ApplicationStep and ApplicationStatus objects.
        app_step, created = ApplicationStep.objects.get_or_create(description=APPLICATION_STATUS['EDS_waiting'], public_status='valid', step=7)
        self.test_app_status = ApplicationStatus(application=self.test_app, lot=lot, current_step=app_step)
        self.test_app_status.save()

    def test_eds_submission(self):
        data = { 'app_id': self.test_app.id }
        request_url = reverse('eds_submission') 
        # response = self.client.post(request_url, content_type='application/json', data=json.dumps(data))
        response = self.client.post(request_url, data=data)

        assert response.status_code == 200

    def tearDown(self):
        self.test_app.delete()
        self.test_app_status.delete()