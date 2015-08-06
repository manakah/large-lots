from django.conf.urls import patterns, include, url
from django.views.generic.base import RedirectView

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'lots_client.views.home', name='home'),
    url(r'^status/$', RedirectView.as_view(url='/status/pilot_1', permanent=False), name='status'),
    url(r'^status/pilot_2$', 'lots_client.views.status_pilot_2', name='status_pilot_2'),
    url(r'^status/pilot_1$', 'lots_client.views.status_pilot_1', name='status_pilot_1'),
    url(r'^apply/$', 'lots_client.views.apply', name='apply'),
    url(r'^apply-confirm/(?P<tracking_id>\S+)/$', 'lots_client.views.apply_confirm', name='apply_confirm'),
    url(r'^faq/$', 'lots_client.views.faq', name='faq'),
    url(r'^about/$', 'lots_client.views.about', name='about'),
    url(r'^lot-uses/$', 'lots_client.views.lot_uses', name='lot_uses'),
    url(r'^lot-uses/1-community-agriculture$', 'lots_client.views.lot_uses_1_community_agriculture', name='lot_uses_1_community_agriculture'),
    url(r'^lots-admin/(?P<pilot>\S+)/$', 'lots_admin.views.pilot_admin', name='pilot_admin'),
    url(r'^lots-admin/$', 'lots_admin.views.lots_admin', name='lots_admin'),
    url(r'^lots-admin-map/$', 'lots_admin.views.lots_admin_map', name='lots_admin_map'),
    url(r'^csv-dump/(?P<pilot>\S+)/$', 'lots_admin.views.csv_dump', name='csv_dump'),
    url(r'^lots-login/$', 'lots_admin.views.lots_login', name='lots_login'),
    url(r'^logout/$', 'lots_admin.views.lots_logout', name='logout'),

    # api endpoints
    url(r'^api/get-pin$', 'lots_client.views.get_pin_from_address', name='get_pin_from_address'),

    url(r'^django-admin/', include(admin.site.urls)),
)
