from django.db import models
import time
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

class Address(models.Model):
    street = models.CharField(max_length=255)
    street_number = models.CharField(max_length=10, null=True)
    street_dir = models.CharField(max_length=15, null=True)
    street_name = models.CharField(max_length=50, null=True)
    street_type = models.CharField(max_length=15, null=True)
    city = models.CharField(max_length=20, default='Chicago')
    state = models.CharField(max_length=20, default='IL')
    zip_code = models.CharField(max_length=15, null=True)
    ward = models.CharField(max_length=15, null=True)
    community = models.CharField(max_length=255, null=True)

    def __str__(self):
        return '%s %s, %s %s' % \
            (self.street, self.city, self.state, self.zip_code)

def upload_name(instance, filename):
    now = int(time.time())
    return '{pilot}/deeds/{first_name}-{last_name}-{now}_{filename}'\
        .format(pilot=settings.CURRENT_PILOT,
                first_name=instance.first_name,
                last_name=instance.last_name,
                now=now,
                filename=filename)

class Application(models.Model):
    first_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    organization_confirmed = models.BooleanField(default=False)
    organization = models.CharField(max_length=255, null=True)
    owned_pin = models.CharField(max_length=14)
    owned_address = models.ForeignKey(Address, related_name='owned_address')
    deed_image = models.FileField(max_length=1000, upload_to=upload_name)
    deed_timestamp = models.DateTimeField(null=True)
    contact_address = models.ForeignKey(Address, related_name='contact_address')
    phone = models.CharField(max_length=15)
    email = models.CharField(max_length=255)
    how_heard = models.CharField(max_length=255, null=True)
    tracking_id = models.CharField(max_length=40)
    received_date = models.DateTimeField(auto_now_add=True)
    pilot = models.CharField(max_length=50, null=True)
    eds_sent = models.BooleanField(default=False)
    eds_received = models.BooleanField(default=False)
    ppf_received = models.BooleanField(default=False)
    closing_invite_sent = models.BooleanField(default=False)

    def __str__(self):
        if self.first_name and self.last_name:
            return '%s %s' % (self.first_name, self.last_name)
        elif self.organization:
            return self.organization

class Lot(models.Model):
    pin = models.CharField(max_length=14, primary_key=True)
    address = models.ForeignKey(Address)
    application = models.ManyToManyField(Application)

    def __str__(self):
        return self.pin

class LotUse(models.Model):
    application = models.ForeignKey(Application)
    lot = models.ForeignKey(Lot)
    planned_use = models.CharField(max_length=255)

class ApplicationStep(models.Model):
    description = models.CharField(max_length=255)
    public_status = models.CharField(max_length=255)
    step = models.IntegerField()

    def __str__(self):
        return self.description

class Review(models.Model):
    reviewer = models.ForeignKey(User)
    step_completed = models.IntegerField(null=True)
    denial_reason = models.ForeignKey('DenialReason', null=True)
    email_sent = models.BooleanField()
    application = models.ForeignKey('ApplicationStatus', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.reviewer)

class DenialReason(models.Model):
    value = models.TextField()

    def __str__(self):
        return self.value

class ApplicationStatus(models.Model):
    denied = models.BooleanField(default=False)
    application = models.ForeignKey('Application', blank=True, null=True)
    lot = models.ForeignKey('Lot', blank=True, null=True)
    is_resident = models.NullBooleanField(null=True)
    current_step = models.ForeignKey('ApplicationStep', blank=True, null=True)
    lottery = models.BooleanField(default=False)
    lottery_email_sent = models.BooleanField(default=False)

    def __str__(self):
        return str(self.application) + " " + str(self.lot)

class PrincipalProfile(models.Model):
    application = models.ForeignKey('Application')
    related_person = models.ForeignKey('RelatedPerson', null=True, blank=True)
    # Store home address of primary applicant on behalf of organization.
    # Null if applicant is applying as an individual.
    org_applicant_address = models.ForeignKey(Address, null=True)
    date_of_birth = models.DateField(null=True)
    social_security_number = models.CharField(max_length=11, null=True)
    drivers_license_state = models.CharField(max_length=2, null=True)
    drivers_license_number = models.CharField(max_length=20, null=True)
    license_plate_state = models.CharField(max_length=2, null=True)
    license_plate_number = models.CharField(max_length=20, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    exported_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return '{0} {1} Principal Profile'.format(self.entity.first_name,
                                                  self.entity.last_name)

    @property
    def entity(self):
        if self.related_person:
            return self.related_person
        else:
            return self.application

    @property
    def address(self):
        '''
        If the PPF pertains to an individual, return the contact address from
        their original application. If the PPF pertains to the primary appli-
        cant for an organization, return the org_applicant_address. Otherwise,
        return the related person's address.
        '''
        if isinstance(self.entity, Application):
            if self.entity.organization_confirmed:
                address_obj = self.org_applicant_address

            else:
                address_obj = self.entity.contact_address

        else:
            address_obj = self.entity.address

        return '{street}, {city}, {state} {zip_code}'.format(street=address_obj.street,
                                                             city=address_obj.city,
                                                             state=address_obj.state,
                                                             zip_code=address_obj.zip_code)


class RelatedPerson(models.Model):
    application = models.ForeignKey('Application')
    first_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255, null=True)
    address = models.ForeignKey(Address, related_name='home_address')

    def __str__(self):
        return '{0} {1} related to Application for {2}'.format(self.first_name,
                                                               self.last_name,
                                                               str(self.application))

class UpdatedEntity(models.Model):
    updated_at = models.DateTimeField(auto_now_add=True)
    admin = models.ForeignKey(User)
    application = models.ForeignKey('Application', null=True)
    owned_pin = models.CharField(max_length=14, null=True)
    street = models.CharField(max_length=255, null=True)

    class Meta:
        verbose_name_plural = 'UpdatedEntities'

    def __str__(self):
        return '{0} updated {1}\'s application'.format(self.admin, self.application)