import os
from io import BytesIO
import re

import magic
import boto

from pdfid.pdfid import PDFiD

from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from django.conf import settings

from lots_admin.models import Application

class Command(BaseCommand):
    help = 'Remove potentially malicious things from uploaded files'

    def handle(self, *args, **options):
        applications = Application.objects.all()

        s3_conn = boto.connect_s3(aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

        self.bucket = s3_conn.get_bucket(settings.AWS_STORAGE_BUCKET_NAME)

        for application in applications:
            scrubbed_image = self.scrub(application.deed_image)

            key = self.bucket.get_key(application.deed_image.name)
            key.delete()

            application.deed_image = scrubbed_image
            application.save()


    def scrub(self, deed_image):
        filetype = magic.from_buffer(deed_image.file.read(), mime=True)

        deed_image.file.seek(0)

        if filetype == 'application/pdf':

            outfile = BytesIO()

            PDFiD(deed_image.file,
                  disarm=True,
                  outfile=outfile)

            _, filename = re.split('\d{10}', deed_image.name, maxsplit=1)
            return File(outfile, name=filename.replace('_', '', 1))
