# Copyright 2007-2010 VPAC
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

from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.sites.models import Site
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry
from django.db.models import Q
from django.core.paginator import QuerySetPaginator

from andsome.util.filterspecs import Filter, FilterBar
from andsome.middleware.threadlocals import get_current_user

from karaage.people.models import Person, Institute
from karaage.requests.models import ProjectCreateRequest
from karaage.projects.models import Project
from karaage.projects.forms import ProjectForm
from karaage.projects.util import get_new_pid, add_user_to_project
from karaage.util.email_messages import send_removed_from_project_email
from karaage.util import log_object as log
from karaage.usage.forms import UsageSearchForm


@login_required
def add_edit_project(request, project_id=None):

    if project_id is None:
        project = None
        flag = 1
    else:
        project = get_object_or_404(Project, pk=project_id)
        flag = 2

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        
        if form.is_valid():
            project = form.save(commit=False)
            if not project.pid:
                project.pid = get_new_pid(project.institute, project.is_expertise)
            project.save()
            project.activate()
            form.save_m2m()
            if flag == 1:
                request.user.message_set.create(message="Project '%s' edited succesfully" % project)
                log(get_current_user(), project, 1, 'Created')
            else:
                request.user.message_set.create(message="Project '%s' added succesfully" % project)
                log(get_current_user(), project, 2, 'Edited')

            return HttpResponseRedirect(project.get_absolute_url())        
    else:        
        form = ProjectForm(instance=project)
            
    return render_to_response('projects/project_form.html', locals(), context_instance=RequestContext(request))

add_edit_project = permission_required('projects.add_project')(add_edit_project)

@login_required
def delete_project(request, project_id):

    project = get_object_or_404(Project, pk=project_id)

    if request.method == 'POST':
        
        project.deactivate()
        log(request.user, project, 3, 'Deleted')
        request.user.message_set.create(message="Project '%s' deleted succesfully" % project)
        return HttpResponseRedirect(project.get_absolute_url()) 

    return render_to_response('projects/project_confirm_delete.html', locals(), context_instance=RequestContext(request))

delete_project = permission_required('projects.delete_project')(delete_project)
    
@login_required
def project_detail(request, project_id):

    project = get_object_or_404(Project, pk=project_id)
    user_list = Person.active.all()
    
    requestor = False
    if project.projectcreaterequest_set.count() > 0:
        requestor = True

    if request.REQUEST.has_key('showall'):
        showall = True

    form = UsageSearchForm()
    
    if request.method == 'POST':
        # Post means adding a user to this project
        if not request.user.has_perm('projects.change_project'):
            return HttpResponseForbidden('<h1>Access Denied</h1>')
        
        data = request.POST.copy()     
        person = Person.objects.get(pk=data['person'])
        add_user_to_project(person, project)
        #if person.has_account(project.machine_category):
        #    project.users.add(person)
        #    request.user.message_set.create(message="User '%s' added succesfully" % person)
        #    log(request.user, project, 1, 'Added user %s' % person)
        #else:
        #    no_account_error = "%s has no account on %s. Please create one first" % (person, project.machine_category)
    
    return render_to_response('projects/project_detail.html', locals(), context_instance=RequestContext(request))

@login_required
def project_list(request, queryset=Project.objects.all(), template_name='projects/project_list.html', paginate=True):

    project_list = queryset

    page_no = int(request.GET.get('page', 1))

    if request.REQUEST.has_key('institute'):
        project_list = project_list.filter(institute=int(request.GET['institute']))

    if request.REQUEST.has_key('status'):
        project_list = project_list.filter(is_active=int(request.GET['status']))

    if request.method == 'POST':
        new_data = request.POST.copy()
        terms = new_data['search'].lower()
        query = Q()
        for term in terms.split(' '):
            q = Q(pid__icontains=term) | Q(name__icontains=term) | Q(description__icontains=term) | Q(leader__user__first_name__icontains=term) | Q(leader__user__last_name__icontains=term) | Q(institute__name__icontains=term)
            query = query & q
        
        project_list = project_list.filter(query)
    else:
        terms = ""


    filter_list = []
    filter_list.append(Filter(request, 'status', {1: 'Active', 0: 'Deleted'}))
    filter_list.append(Filter(request, 'institute', Institute.primary.all()))
    filter_bar = FilterBar(request, filter_list)

    if paginate:
        p = QuerySetPaginator(project_list, 50)
        page = p.page(page_no)
    else:
        p = QuerySetPaginator(project_list, 100000)
        page = p.page(page_no)

    return render_to_response(template_name, locals(), context_instance=RequestContext(request))


@login_required
def remove_user(request, project_id, username):
    site = Site.objects.get_current()

    project = get_object_or_404(Project, pk=project_id)
    user = get_object_or_404(Person, user__username=username)

    if site.id == 2:
        if not request.user.get_profile() == project.leader:
            return HttpResponseForbidden('<h1>Access Denied</h1>')

    project.users.remove(user)
    request.user.message_set.create(message="User '%s' removed succesfully from project %s" % (user, project.pid))
    
    log(request.user, project, 3, 'Removed %s from project' % user)
    log(request.user, user, 3, 'Removed from project %s' % project)

   # send_removed_from_project_email(user, project)
    
    if 'next' in request.REQUEST:
        return HttpResponseRedirect(request.REQUEST['next'])
    if site.id == 2:
        return HttpResponseRedirect(project.get_absolute_url())
    return HttpResponseRedirect(user.get_absolute_url())

@login_required
def no_users(request):

    project_ids = []
    for p in Project.active.all():
        if p.users.count() == 0:
            project_ids.append(p.pid)

    return project_list(request, Project.objects.filter(pid__in=project_ids))


@login_required
def over_quota(request):

    project_ids = []

    for p in Project.active.all():
        for mc in p.machine_categories.all():
            if p.projectchunk_set.get(machine_category=mc).is_over_quota():
                project_ids.append(p.pid)

    return project_list(request, Project.objects.filter(pid__in=project_ids))


def project_logs(request, project_id):

    project = get_object_or_404(Project, pk=project_id)

    log_list = LogEntry.objects.filter(
        content_type=ContentType.objects.get_for_model(project.__class__),
        object_id=project_id
    )

    short = True
    return render_to_response('log_list.html', locals(), context_instance=RequestContext(request))


@login_required       
def pending_requests(request):
    request_list = ProjectCreateRequest.objects.all()

    return render_to_response('projects/pending_requests.html', locals(), context_instance=RequestContext(request))