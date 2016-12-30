from django.test import TestCase, Client
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO
from PIL import Image

from lots_client.views import ApplicationForm

class ApplicationFormTests(TestCase):
    def test_application_form(self):
        mock_image = Image.new(mode='RGB', size=(200, 200))
        image_io = BytesIO()
        mock_image.save(image_io, 'JPEG')
        image_io.seek(0)

        image = InMemoryUploadedFile(
            image_io, None, 'my_deed.jpg', 'image/jpeg', 200, None
        )

        form_data = {'lot_1_address': '2255 S KOLIN AVE',
            'lot_1_pin': '16-27-202-023-0000',
            'owned_address': '2257 S KOLIN AVE',
            'owned_pin': '16-27-202-024-0000',
            'first_name': 'Regina',
            'last_name': 'Compton',
            'phone': '9999999999',
            'email': 'regina@aol.com',
            'contact_street': '999 Chicago Lane',
            'contact_city': 'Chicago',
            'contact_state': 'IL',
            'contact_zip_code': '99999',
            'terms': True
        }

        file_dict = {'deed_image': image}

        form = ApplicationForm(data=form_data, files=file_dict)
        self.assertTrue(form.is_valid())


