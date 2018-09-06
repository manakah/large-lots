import json
import logging

from django.core.management.base import BaseCommand, CommandError

from lots_admin.models import ApplicationStatus, DenialReason, Review, User

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--pins_with_denials',
                            help='JSON object, wherein the PIN is the key and text for denial reason is the value')

        parser.add_argument('--user_email',
                            default='reginafcompton@datamade.us')

    def handle(self, *args, **options):
        pins_with_denials = json.loads(options['pins_with_denials'])
        user_email = options['user_email']
        user = User.objects.get(email=user_email)

        self.stdout.write('Begin: Denying applications!')

        for pin, reason_text in pins_with_denials.items():
            applications = ApplicationStatus.objects.filter(lot=pin)
            for app in applications:
                reason, _ = DenialReason.objects.get_or_create(value=reason_text)
                review = Review(reviewer=user, email_sent=True, denial_reason=reason, application=app)
                review.save()
                app.denied = True
                app.current_step = None
                app.save()

                self.stdout.write(('{0} {1} | {2}').format(app.application.first_name, app.application.last_name, pin))
