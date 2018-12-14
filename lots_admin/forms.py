import json

from django.conf import settings
from django import forms
from django.core.management import call_command

from lots_client.utils import parse_address
from .models import Application, Address

class AddressUpdateForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ('street', )
        widgets = {
            'street': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(AddressUpdateForm, self).__init__(*args, **kwargs)
        self.can_delete = False

    def save(self, *args, **kwargs):
        street = self.cleaned_data['street']

        (street_number, street_dir, street_name, street_type, unit_number) = parse_address(street)

        add_info = {
            'street': street,
            'street_number': street_number,
            'street_dir': street_dir,
            'street_name': street_name,
            'street_type': street_type,
        }

        address = super(AddressUpdateForm, self).save(*args, **kwargs)
        for key, value in add_info.items():
            setattr(address, key, value)
        address.save()

        return address

class ApplicationUpdateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ('owned_pin', )
        widgets = {
            'owned_pin': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(ApplicationUpdateForm, self).__init__(*args, **kwargs)
        self.can_delete = False

class DateTimeForm(forms.Form):
    use_required_attribute = False # Do not let the browser validate: https://docs.djangoproject.com/en/2.1/ref/forms/api/#django.forms.Form.use_required_attribute
    select_pilot = forms.CharField(widget=forms.HiddenInput(), initial='pilot')
    date = forms.CharField(widget=forms.TextInput(attrs={'class':'email-datepicker form-control', 
                                                         'placeholder':'Select a date'}))
    time = forms.CharField(widget=forms.TextInput(attrs={'class':'email-timepicker form-control',
                                                         'placeholder':'Select a time'}))

class EdsEmailForm(DateTimeForm):
    action = forms.CharField(widget=forms.HiddenInput(), initial='eds_form')
    modal_message = 'You are about to send an email with links to complete the EDS and PPF. Emails will go to applicants whose non-denied applications are all on Step 7.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].widget.attrs.update({'id': 'eds'}) # Assign an id to subclassed `date` fields for jQuery datepicker

    def _call_command(self):
        call_command('send_emails', 
                     '--eds_email', 
                     '-a {}'.format(self.user.id), # Make sure to hit the argument parser: https://docs.djangoproject.com/en/1.10/ref/django-admin/#django.core.management.call_command
                     base_context=json.dumps(self.base_context),
                     stdout=self.out)

class FinalEdsEmailForm(DateTimeForm):
    action = forms.CharField(widget=forms.HiddenInput(), initial='final_eds_form')
    modal_message = 'You are about to send a final notice to applicants on Step 7 who have not yet submitted an EDS and/or PPF forms.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].widget.attrs.update({'id': 'final_eds'})

    def _call_command(self):
        call_command('send_emails', 
                     '--eds_final_email', 
                     '-a {}'.format(self.user.id), 
                     base_context=json.dumps(self.base_context),
                     stdout=self.out)

class EdsDenialEmailForm(forms.Form):
    select_pilot = forms.CharField(widget=forms.HiddenInput(), initial='pilot')
    action = forms.CharField(widget=forms.HiddenInput(), initial='eds_denial_form')
    modal_message = 'You are about to do the following: (1) send denial emails to applicants on Step 7 who failed to submit an EDS and/or PPF form, and (2) deny those applicants.'

    def _call_command(self):
        call_command('send_emails', 
                     '--eds_denial_email', 
                     '-a {}'.format(self.user.id), 
                     base_context=json.dumps(self.base_context),
                     stdout=self.out)

class LotteryEmailForm(DateTimeForm):
    action = forms.CharField(widget=forms.HiddenInput(), initial='lottery_form')
    number = forms.IntegerField(widget=forms.TextInput(attrs={'class':'form-control', 
                                                              'placeholder':'Number of lots'}))
    location = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control', 
                                                             'placeholder':'Provide a location, e.g., City Hall (121 N. LaSalle St) 11th floor, 1103 conference room'}))
    modal_message = 'You are about to notify applicants about the lottery. Emails will go to a specified number of applicants on Step 6.'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].widget.attrs.update({'id': 'lottery_email'})

    def _call_command(self):
        call_command('send_emails',
                     '--lotto_email',
                     '-n {}'.format(self.number),
                     '-a {}'.format(self.user.id),
                     '--select_pilot={}'.format(self.select_pilot),
                     base_context=json.dumps(self.base_context),
                     stdout=self.out)

class ClosingTimeEmail(forms.Form):
    select_pilot = forms.CharField(widget=forms.HiddenInput())
    action = forms.CharField(widget=forms.HiddenInput(), initial='closing_time_form')
    modal_message = 'You are about to do the following: (1) notify applicants that the Chicago City Council granted approval for the sale of their lots, and (2) move applicants from Step 8 to Step 9.'

    def _call_command(self):
        call_command('send_emails',
                     '--closing_time_email',
                     '-a {}'.format(self.user.id),
                     stdout=self.out)


STEPS = [(step, step) for step in range(2, 12)]
CHOICES = (('on_step', 'applicants on this step'), 
           ('not_on_step', 'applicants NOT on this step'),
           ('on_steps_before', 'applicants before this step (e.g., if you want to send an email to applicants on steps 2, 3, and 4, then select step "5" and check this option)'),
           ('on_steps_after', 'applicants after this step (e.g., if you want to send an email to applicants on steps 6, 7, 8, 9, 10, and 11, then select step "5" and check this option)'))

class CustomEmail(forms.Form):
    use_required_attribute = False
    select_pilot = forms.CharField(widget=forms.HiddenInput())
    action = forms.CharField(
                widget=forms.HiddenInput(), 
                initial='custom_form')
    step = forms.CharField(widget=forms.Select(choices=STEPS))
    every_status = forms.BooleanField(
                widget=forms.CheckboxInput(attrs={'style': 'margin-right: 8px'}),
                required=False)
    selection = forms.ChoiceField(widget=forms.RadioSelect, choices=CHOICES)
    subject = forms.CharField(widget=forms.TextInput(attrs={'class':'form-control'}))
    email_text = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control','placeholder': 'Enter custom text for your email...', 'style': 'font-size: 18px'}))
    modal_message = 'You are about to send a custom email to a group of applicants, based on whether those applicants are "on," "not on," "before," or "after" a specified step.'

    def _call_command(self):
        call_command('send_emails', 
                     '-a {}'.format(self.user.id), 
                     custom_email=self.selection, 
                     steps=int(self.step),
                     every_status=self.every_status,
                     base_context=json.dumps(self.base_context),
                     stdout=self.out)