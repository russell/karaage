# Copyright 2007-2013 VPAC
#
# This file is part of Karaage.
#
# Karaage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Karaage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Karaage  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls import *

urlpatterns = patterns('karaage.applications.views.admin',

    url(r'^$', 'application_list', name='kg_application_list'),
    url(r'^applicants/(?P<applicant_id>\d+)/$', 'applicant_edit', name='kg_applicant_edit'),
    url(r'^(?P<application_id>\d+)/logs/$', 'application_logs', name='kg_application_logs'),
    url(r'^(?P<application_id>\d+)/add_comment/$', 'add_comment', name='kg_application_add_comment'),
    url(r'^new/$', 'new_application', name='kg_application_new'),
)

urlpatterns += patterns('karaage.applications.views',
    url(r'^project/invite/$', 'project.admin_send_invitation', name='kg_application_invite'),
    url(r'^project/invite/(?P<project_id>[-.\w]+)/$', 'project.admin_send_invitation', name='kg_application_invite'),

    url(r'^(?P<application_id>\d+)/$', 'admin.application_detail', name='kg_application_detail'),
    url(r'^(?P<application_id>\d+)/(?P<state>[-.\w]+)/$', 'admin.application_detail', name='kg_application_detail'),
    url(r'^(?P<application_id>\d+)/(?P<state>[-.\w]+)/(?P<label>[-.\w]+)/$', 'admin.application_detail', name='kg_application_detail'),
)

