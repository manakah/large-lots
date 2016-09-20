from django.contrib import admin

from lots_admin.models import Address, Application, Lot, ApplicationStep, Review, DenialReason, ApplicationStatus

admin.site.register(Address)
admin.site.register(Application)
admin.site.register(Lot)
admin.site.register(ApplicationStep)
admin.site.register(Review)
admin.site.register(DenialReason)
admin.site.register(ApplicationStatus)
