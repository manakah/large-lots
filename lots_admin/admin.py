from django.contrib import admin

from lots_admin.models import Address, Application, Lot, ApplicationStatus, DenialReason

admin.site.register(Address)
admin.site.register(Application)
admin.site.register(Lot)
admin.site.register(ApplicationStatus)
admin.site.register(DenialReason)
