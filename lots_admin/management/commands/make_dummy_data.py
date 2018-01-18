import datetime
import random
import uuid

import django
from django.core.management.base import BaseCommand

from faker import Faker

from lots_admin.models import Address, Application, Lot, ApplicationStep, \
    ApplicationStatus


class Command(BaseCommand):
    help = 'Fill your database with dummy data'

    # To generate the same "random" data every run, manually set the seed,
    # i.e., `fake.seed(2012)`
    fake = Faker()

    def add_arguments(self, parser):
        parser.add_argument('--n_applications',
                            help='Number of applications to create',
                            default=150,
                            type=int)

        parser.add_argument('--n_addresses',
                            help='Number of addresses to create',
                            default=100,
                            type=int)

        parser.add_argument('--n_lots',
                            help='Number of lots to create',
                            default=75,
                            type=int)

    def handle(self, *args, **options):
        self.make_steps()
        self.make_addresses(options['n_addresses'])
        self.make_lots(options['n_lots'])
        self.make_applications(options['n_applications'])

    def make_steps(self):
        # Create steps if they don't exist
        if not ApplicationStep.objects.all():
            steps = [
                ('Deed check', 2),
                ('Location check', 3),
                ('Multiple applicant check', 4),
                ('Alderman letter of support', 5),
                ('Lottery', 6),
                ('Submit EDS and principal profile', 7),
                ('EDS and principal profile submitted', 8),
            ]

            for description, number in steps:
                step = ApplicationStep(description=description, step=number)
                step.save()

    def make_addresses(self, n):
        for i in range(n):
            address = Address(street=self.fake.street_address(), ward=random.randint(1,50))
            address.save()

    def make_lots(self, n):
        addresses = Address.objects.all()
        for i in range(n):
            lot_saved = False
            while not lot_saved:
                try:
                    lot_info = {
                        'pin': random.randint(1000,9999),
                        'address': addresses[random.randint(0, len(addresses) - 1)]
                    }
                    lot = Lot(**lot_info)
                    lot.save()
                    lot_saved = True
                except django.db.utils.ProgrammingError:
                    continue

    def make_applications(self, n, datamade=True):
        addresses = Address.objects.all()

        for i in range(n):
            if datamade:
                email = 'testing+{}@datamade.us'.format(uuid.uuid4())
            else:
                email = self.fake.email()

            address = addresses[random.randint(0, len(addresses) - 1)]

            application_info = {
                'first_name': self.fake.first_name(),
                'last_name': self.fake.last_name(),
                'organization': '',
                'owned_pin': '',
                'owned_address': address,
                'deed_image': 'a-deed-image.png',
                'deed_timestamp': datetime.datetime.now(),
                'contact_address': address,
                'phone': self.fake.phone_number().split('x')[0][:15],
                'email': email,
                'how_heard': '',
                'tracking_id': uuid.uuid4(),
                'received_date': datetime.datetime.now(),
                'pilot': 'pilot_6_dev',
                'eds_sent': False
            }
            application = Application(**application_info)
            application.save()

            lots = list(Lot.objects.all())
            steps = list(ApplicationStep.objects.all())

            for i in range(random.randint(1, 5)):
                lot = lots[random.randint(0, len(lots) - 1)]

                application_status_info = {
                    'denied': bool(random.randint(0, 1)),
                    'application': application,
                    'lot': lot,
                    'current_step': steps[random.randint(0, len(steps) - 1)],
                    'lottery': bool(random.randint(0, 1))
                }

                application_status = ApplicationStatus(**application_status_info)
                application_status.save()

                application.lot_set.add(lot)
                application.save()

            application.status = application_status
            application.save()
