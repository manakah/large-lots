from django.conf.urls import include, url
from django.conf import settings
from django.views.generic.base import RedirectView
from lots_client.views import home, apply_confirm, faq, about, lot_uses_page, lot_uses, apply, \
    get_pin_from_address, deed_upload, upload_confirm, \
    wintrust_invitation, wintrust_announcement, \
    principal_profile_form, eds_submission

from lots_admin.views import lots_admin, lots_admin_map, csv_dump, lots_login, \
    lots_logout,pdfviewer, deed_check, deed_check_submit, deed_duplicate_submit, applicant_duplicate_submit, \
    location_check, location_check_submit, \
    multiple_applicant_check, multiple_location_check_submit, \
    lotteries, lottery, lottery_submit, \
    review_EDS,deny_application, deny_submit, review_status_log, bulk_submit, \
    bulk_deny, bulk_deny_submit, status_tally, get_parcel_geometry, \
    deed, double_submit, lots_admin_principal_profiles, delete_principal_profiles, \
    email_error

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    # Examples:
    url(r'^$', home, name='home'),
    url(r'^apply/$', apply, name='apply'),
    url(r'^apply-confirm/(?P<tracking_id>\S+)/$', apply_confirm, name='apply_confirm'),
    url(r'^faq/$', faq, name='faq'),
    url(r'^about/$', about, name='about'),
    url(r'^lot-uses/(?P<use_id>\d+)/$', lot_uses_page, name='lot_uses_page'),
    url(r'^lot-uses/$', lot_uses, name='lot_uses'),
    url(r'^deed-upload/(?P<tracking_id>\S+)/$', deed_upload, name='deed_upload'),
    url(r'^upload-confirm/(?P<tracking_id>\S+)/$', upload_confirm, name='upload_confirm'),
    url(r'^wintrust-invitation/$', wintrust_invitation, name='wintrust_invitation'),
    url(r'^wintrust-announcement/$', wintrust_announcement, name='wintrust_announcement'),
    url(r'^eds-submission/$', eds_submission, name='eds_submission'),
    url(r'^principal-profile-form/(?P<tracking_id>\S+)/$', principal_profile_form, name='principal_profile_form'),
    url(r'^principal-profile-form/$', principal_profile_form, name='principal_profile_form'),
    url(r'^lots-admin/(?P<step>\S+)/$', lots_admin, name='lots_admin'),
    url(r'^lots-admin-map/$', lots_admin_map, name='lots_admin_map'),
    url(r'^principal-profiles/$', lots_admin_principal_profiles, name='lots_admin_principal_profiles'),
    url(r'^csv-dump/(?P<pilot>\S+)/(?P<status>\S+)/(?P<content>\S+)$', csv_dump, name='csv_dump'),
    url(r'^csv-dump/(?P<pilot>\S+)/(?P<status>\S+)$', csv_dump, name='csv_dump'),
    url(r'^ppf-delete/(?P<pilot>\S+)/$', delete_principal_profiles, name='delete_principal_profiles'),
    url(r'^lots-login/$', lots_login, name='lots_login'),
    url(r'^logout/$', lots_logout, name='logout'),

    # api endpoints
    url(r'^api/get-pin$', get_pin_from_address, name='get_pin_from_address'),

    url(r'^django-admin/', include(admin.site.urls)),

    # review steps
    url(r'^pdfviewer/$', pdfviewer, name='pdfviewer'),
    url(r'^deed/(?P<application_id>\d+)$', deed, name='deed'),
    url(r'^application-review/step-2/(?P<application_id>\d+)/$', deed_check, name='deed_check'),
    url(r'^deed_check_submit/(?P<application_id>\d+)$', deed_check_submit, name='deed_check_submit'),
    url(r'^deed_duplicate_submit/(?P<application_id>\d+)$', deed_duplicate_submit, name='deed_duplicate_submit'),
    url(r'^applicant_duplicate_submit/(?P<application_id>\d+)$', applicant_duplicate_submit, name='applicant_duplicate_submit'),
    url(r'^application-review/step-3/(?P<application_id>\d+)/$', location_check, name='location_check'),
    url(r'^location_check_submit/(?P<application_id>\d+)$', location_check_submit, name='location_check_submit'),
    url(r'^application-review/step-4/(?P<application_id>\d+)/$', multiple_applicant_check, name='multiple_applicant_check'),
    url(r'^multiple_location_check_submit/(?P<application_id>\d+)$', multiple_location_check_submit, name='multiple_location_check_submit'),
    url(r'^lotteries/$', lotteries, name='lotteries'),
    url(r'^lottery/(?P<lot_pin>\d+)$', lottery, name='lottery'),
    url(r'^lottery-submit/(?P<lot_pin>\d+)$', lottery_submit, name='lottery_submit'),
    url(r'^application-review/step-7/(?P<application_id>\d+)/$', review_EDS, name='review_EDS'),
    url(r'^deny-application/(?P<application_id>\d+)/$', deny_application, name='deny_application'),
    url(r'^deny-submit/(?P<application_id>\d+)/$', deny_submit, name='deny_submit'),
    url(r'^double-submit/(?P<application_id>\d+)/$', double_submit, name='double_submit'),
    url(r'^review-status-log/(?P<application_id>\d+)$', review_status_log, name='review_status_log'),
    url(r'^bulk_submit/$', bulk_submit, name='bulk_submit'),
    url(r'^bulk-deny/$', bulk_deny, name='bulk_deny'),
    url(r'^bulk-deny-submit/$', bulk_deny_submit, name='bulk_deny_submit'),
    url(r'^status-tally/$', status_tally, name='status_tally'),
    url(r'^get-parcel-geometry/$', get_parcel_geometry, name='get-parcel-geometry'),
    url(r'^email-error/$', email_error, name='email_error'),]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns