from django.contrib import admin

from lots_admin.models import Address, Application, Lot, ApplicationStep, Review, DenialReason, ApplicationStatus, UpdatedEntity

class AdminApplication(admin.ModelAdmin):
    search_fields = ['first_name', 'last_name', 'id']

class AdminApplicationStatus(admin.ModelAdmin):
    search_fields = ['application__first_name', 'application__last_name', 'application__id']

class AdminUpdatedEntity(admin.ModelAdmin):
    readonly_fields = ['updated_at']
    search_fields = ['application__first_name', 'application__last_name', 'address__street']

admin.site.register(Address)
admin.site.register(Application, AdminApplication)
admin.site.register(Lot)
admin.site.register(ApplicationStep)
admin.site.register(Review)
admin.site.register(DenialReason)
admin.site.register(ApplicationStatus, AdminApplicationStatus)
admin.site.register(UpdatedEntity, AdminUpdatedEntity)