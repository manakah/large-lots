from django.db import models
import time
from django.conf import settings
from django.contrib.auth.models import User

class Address(models.Model):
    street = models.CharField(max_length=255)
    street_number = models.CharField(max_length=10, null=True)
    street_dir = models.CharField(max_length=2, null=True)
    street_name = models.CharField(max_length=50, null=True)
    street_type = models.CharField(max_length=10, null=True)
    longitude = models.FloatField(null=True)
    latitude = models.FloatField(null=True)
    city = models.CharField(max_length=20, default='Chicago')
    state = models.CharField(max_length=20, default='IL')
    zip_code = models.CharField(max_length=10, null=True)

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
    organization = models.CharField(max_length=255, null=True)
    owned_pin = models.CharField(max_length=14)
    owned_address = models.ForeignKey(Address, related_name='owned_address')
    deed_image = models.FileField(upload_to=upload_name)
    contact_address = models.ForeignKey(Address, related_name='contact_address')
    phone = models.CharField(max_length=15)
    email = models.CharField(max_length=255, null=True)
    how_heard = models.CharField(max_length=255, null=True)
    tracking_id = models.CharField(max_length=40)
    review_status = models.ForeignKey('ReviewStatus', blank=True, null=True)
    status = models.ForeignKey('ApplicationStatus', blank=True, null=True)
    received_date = models.DateTimeField(auto_now_add=True)
    pilot = models.CharField(max_length=50, null=True)

    def __str__(self):
        if self.first_name and self.last_name:
            return '%s %s' % (self.first_name, self.last_name)
        elif self.organization:
            return self.organization

class Lot(models.Model):
    pin = models.CharField(max_length=14, primary_key=True)
    address = models.ForeignKey(Address)
    application = models.ManyToManyField(Application)
    planned_use = models.CharField(max_length=20, default=None, null=True)

    def __str__(self):
        return self.pin

class ApplicationStatus(models.Model):
    description = models.CharField(max_length=255)
    public_status = models.CharField(max_length=255)
    step = models.IntegerField()

    def __str__(self):
        return self.description

class DenialReason(models.Model):
    value = models.TextField()
    step = models.IntegerField()

    def __str__(self):
        return self.value

class ReviewStatus(models.Model):
    reviewer = models.ForeignKey(User)
    denied = models.BooleanField(default=False)
    denial_reason = models.ForeignKey('DenialReason', null=True)
    email_sent = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.reviewer)
