from django.conf.urls import include, url
from django.views.generic.base import RedirectView
from lots_client.views import home, status_pilot_1, status_pilot_2, \
    apply_confirm, faq, about, lot_uses_page, lot_uses, apply, \
    get_pin_from_address

from lots_admin.views import pilot_admin, lots_admin, lots_admin_map, \
    csv_dump, lots_login, lots_logout, deed_check, pdfviewer, \
    deed_check_submit, location_check, deny_application, get_parcel_geometry

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    # Examples:
    url(r'^$', home, name='home'),
    url(r'^status/$', RedirectView.as_view(url='/status/pilot_1', permanent=False), name='status'),
    url(r'^status/pilot_2$', status_pilot_2, name='status_pilot_2'),
    url(r'^status/pilot_1$', status_pilot_1, name='status_pilot_1'),
    url(r'^apply/$', apply, name='apply'),
    url(r'^apply-confirm/(?P<tracking_id>\S+)/$', apply_confirm, name='apply_confirm'),
    url(r'^faq/$', faq, name='faq'),
    url(r'^about/$', about, name='about'),
    url(r'^lot-uses/(?P<use_id>\d+)/$', lot_uses_page, name='lot_uses_page'),
    url(r'^lot-uses/$', lot_uses, name='lot_uses'),
    url(r'^lots-admin/(?P<pilot>\S+)/$', pilot_admin, name='pilot_admin'),
    url(r'^lots-admin/$', lots_admin, name='lots_admin'),
    url(r'^lots-admin-map/$', lots_admin_map, name='lots_admin_map'),
    url(r'^csv-dump/(?P<pilot>\S+)/$', csv_dump, name='csv_dump'),
    url(r'^lots-login/$', lots_login, name='lots_login'),
    url(r'^logout/$', lots_logout, name='logout'),

    # api endpoints
    url(r'^api/get-pin$', get_pin_from_address, name='get_pin_from_address'),

    url(r'^django-admin/', include(admin.site.urls)),

    # review steps
    url(r'^pdfviewer/$', pdfviewer, name='pdfviewer'),
    url(r'^application-review/step-2/(?P<application_id>\d+)/$', deed_check, name='deed_check'),
    url(r'^application-review/step-3/(?P<application_id>\d+)/$', location_check, name='location_check'),

    url(r'^deed_check_submit/(?P<application_id>\d+)$', deed_check_submit, name='deed_check_submit'),

    url(r'^deny-application/(?P<application_id>\d+)/$', deny_application, name='deny_application'),
    
    url(r'^get-parcel-geometry/$', get_parcel_geometry, name='get-parcel-geometry'),
]
