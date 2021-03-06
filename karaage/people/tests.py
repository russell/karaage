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

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings
from django.core.management import call_command

import datetime
from tldap.test import slapd

from karaage.people.models import Person
from karaage.institutes.models import Institute, InstituteDelegate
from karaage.projects.models import Project
from karaage.machines.models import Account, MachineCategory
from karaage.test_data.initial_ldap_data import test_ldif

from karaage.datastores import get_test_datastore

class UserTestCase(TestCase):

    def setUp(self):
        self._datastore = get_test_datastore()

        server = slapd.Slapd()
        server.set_port(38911)
        server.start()
        server.ldapadd("\n".join(test_ldif)+"\n")
        call_command('loaddata', 'karaage/testproject/karaage_data', **{'verbosity': 0})

        self.server = server

    def tearDown(self):
        self.server.stop()

    def do_permission_tests(self, test_object, users):
        for user_id in users:
#            print "can user '%d' access '%s'?"%(user_id, test_object)
            user = Person.objects.get(id=user_id)
            result = test_object.can_view(user)
            expected_result = users[user_id]
#            print "---> got:'%s' expected:'%s'"%(result, expected_result)
            self.failUnlessEqual(result, expected_result)
#            print

    def test_permissions(self):
        test_object = Project.objects.get(pid="TestProject1")
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: person's institute delegate, project leader
            2: False, # person 2 cannot view
            3: True, # person 3 can view: project member
            4: True, # person 4 can view: is_staff
        })

        test_object = Person.objects.get(id=1)
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: self, project member, person's institute delegate
            2: False, # person 2 cannot view
            3: False, # person 3 cannot view
            4: True, # person 4 can view: is_staff, institute delegate
        })

        test_object = Person.objects.get(id=2)
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: person's institute delegate
            2: True, # person 2 can view: self
            3: False, # person 3 cannot view
            4: True, # person 4 can view: is_staff
        })

        test_object = Person.objects.get(id=3)
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: person's institute delegate, project leader
            2: False, # person 2 cannot view
            3: True, # person 3 can view: self, project member
            4: True, # person 4 can view: is_staff
        })

        test_object = Person.objects.get(id=4)
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: person's institute delegate
            2: False, # person 2 cannot view
            3: False, # person 3 cannot view
            4: True, # person 4 can view: self, is_staff
        })

        # add user 2 to project
        # test that members can see other people in own project
#        print "-------------------------------------------------------------------"
        project = Project.objects.get(pid="TestProject1")
        project.group.members=[2,3]

        test_object = Project.objects.get(pid="TestProject1")
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: person's institute delegate
            2: True, # person 2 can view: project member
            3: True, # person 3 can view: project member
            4: True, # person 4 can view: is_staff
        })

        test_object = Person.objects.get(id=1)
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view:  self, project member, delegate of institute
            2: False, # person 2 cannot view
            3: False, # person 3 cannot view
            4: True, # person 4 can view: is_staff
        })

        test_object = Person.objects.get(id=2)
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: person's institute delegate, project leader
            2: True, # person 2 can view: self
            3: True, # person 3 can view: project member
            4: True, # person 4 can view: is_staff
        })

        test_object = Person.objects.get(id=3)
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: person's institute delegate, project leader
            2: True, # person 2 can view: project member
            3: True, # person 3 can view: self, project member
            4: True, # person 4 can view: is_staff
        })

        test_object = Person.objects.get(id=4)
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: person's institute delegate
            2: False, # person 2 cannot view
            3: False, # person 3 cannot view
            4: True, # person 4 can view: self, is_staff
        })

        # change institute of all people
        # Test institute leader can access people in project despite not being
        # institute leader for these people.
#        print "-------------------------------------------------------------------"
        Person.objects.all().update(institute=2)
        #Institute.objects.filter(pk=2).update(delegate=2,active_delegate=2)
        InstituteDelegate.objects.get_or_create(institute=Institute.objects.get(id=2), person=Person.objects.get(id=2))
        project = Project.objects.get(pid="TestProject1")
        project.leaders=[2]

        test_object = Project.objects.get(pid="TestProject1")
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: person's institute delegate
            2: True, # person 2 can view: project member, person's institute delegate, project leader
            3: True, # person 3 can view: project member
            4: True, # person 4 can view: is_staff
        })

        test_object = Person.objects.get(id=1)
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: self, project member
            2: True, # person 2 can view: person's institute delegate
            3: False, # person 3 cannot view
            4: True, # person 4 can view: is_staff
        })

        test_object = Person.objects.get(id=2)
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: project's institute leader
            2: True, # person 2 can view: self, person's institute delegate, project leader
            3: True, # person 3 can view: project member
            4: True, # person 4 can view: is_staff
        })

        test_object = Person.objects.get(id=3)
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: project's institute leader
            2: True, # person 2 can view: project member, person's institute delegate, project leader
            3: True, # person 3 can view: self, project member
            4: True, # person 4 can view: is_staff
        })

        test_object = Person.objects.get(id=4)
        self.do_permission_tests(test_object, {
            1: True, # person 1 can view: person's institute delegate
            2: True, # person 2 can view: person's institute delegate
            3: False, # person 3 cannot view
            4: True, # person 4 can view: self, is_staff
        })


    def test_admin_create_user_with_account(self):

        users = Person.objects.count()
        project = Project.objects.get(pid='TestProject1')
        p_users = project.group.members.count()
        logged_in = self.client.login(username='kgsuper', password='aq12ws')
        self.failUnlessEqual(logged_in, True)
        response = self.client.get(reverse('kg_person_add'))
        self.failUnlessEqual(response.status_code, 200)
        
        form_data = {
            'title' : 'Mr',
            'short_name': 'Sam',
            'full_name': 'Sam Morrison',
            'position': 'Sys Admin',
            'institute': 1,
            'department': 'eddf',
            'email': 'sam@vpac.org',
            'country': 'AU',
            'telephone': '4444444',
            'username': 'samtest',
            'password1': 'Exaiquouxei0',
            'password2': 'Exaiquouxei0',
            'project': 1,
            'needs_account': True,
            'machine_category': 1,
        }

        response = self.client.post(reverse('kg_person_add'), form_data)
        self.failUnlessEqual(response.status_code, 302)

        self.assertEqual(Person.objects.count(), users+1)
        users = users + 1
        person = Person.objects.get(pk=users)
        self.assertEqual(person.is_active, True)
        self.assertEqual(person.username, 'samtest')
        self.assertEqual(Account.objects.count(), 2)
        self.assertEqual(project.group.members.count(), p_users+1)
        luser = self._datastore._accounts().get(uid='samtest')
        self.assertEqual(luser.givenName, 'Sam')
        self.assertEqual(luser.homeDirectory, '/vpac/TestProject1/samtest')
        
     
    def test_admin_create_user(self):
        users = Person.objects.count()
        project = Project.objects.get(pid='TestProject1')
        project.group.members.count()
        logged_in = self.client.login(username='kgsuper', password='aq12ws')
        self.failUnlessEqual(logged_in, True)
        response = self.client.get(reverse('kg_person_add'))
        
        self.failUnlessEqual(response.status_code, 200)

        form_data = {
            'title' : 'Mr',
            'short_name': 'Sam',
            'full_name': 'Sam Morrison2',
            'position': 'Sys Admin',
            'institute': 1,
            'department': 'eddf',
            'email': 'sam@vpac.org',
            'country': 'AU',
            'telephone': '4444444',
            'username': 'samtest2',
            'password1': 'Exaiquouxei0',
            'password2': 'Exaiquouxei0',
            'needs_account': False,
        }

        response = self.client.post(reverse('kg_person_add'), form_data)
        self.failUnlessEqual(response.status_code, 302)

        self.assertEqual(Person.objects.count(), users+1)
        users = users + 1
        person = Person.objects.get(pk=users)
        self.assertEqual(person.is_active, True)
        self.assertEqual(person.username, 'samtest2')
        # Try adding it again - Should fail
        response = self.client.post(reverse('kg_person_add'), form_data)
        self.failUnlessEqual(response.status_code, 200)


    def test_admin_update_person(self):
        logged_in = self.client.login(username='kgsuper', password='aq12ws')
        self.failUnlessEqual(logged_in, True)

        person = Person.objects.get(username='kgtestuser3')
        luser = self._datastore._accounts().get(uid='kgtestuser3')
        self.failUnlessEqual(person.mobile, '')
        self.failUnlessEqual(luser.gidNumber, 500)
        self.failUnlessEqual(luser.o, 'Example')
        self.failUnlessEqual(luser.gecos, 'Test User3 (Example)')
        response = self.client.get(reverse('kg_person_edit', args=['kgtestuser3']))
        self.failUnlessEqual(response.status_code, 200)
        
        form_data = {
            'title' : 'Mr',
            'short_name': 'Test',
            'full_name': 'Test User3',
            'position': 'Sys Admin',
            'institute': 2,
            'department': 'eddf',
            'email': 'sam@vpac.org',
            'country': 'AU',
            'telephone': '4444444',
            'mobile': '555666',
        }
        response = self.client.post(reverse('kg_person_edit', args=['kgtestuser3']), form_data)
        self.failUnlessEqual(response.status_code, 302)

        person = Person.objects.get(username='kgtestuser3')
        luser = self._datastore._accounts().get(uid='kgtestuser3')
        self.failUnlessEqual(person.mobile, '555666')
        self.failUnlessEqual(luser.gidNumber, 501)
        self.failUnlessEqual(luser.o, 'OtherInst')
        self.failUnlessEqual(luser.gecos, 'Test User3 (OtherInst)')

    def test_delete_activate_person(self):
        self.client.login(username='kgsuper', password='aq12ws')
        person = Person.objects.get(username='kgtestuser3')
        self.assertEqual(person.is_active, True)
        self.assertEqual(person.projects.count(), 1)
        self.assertEqual(person.account_set.count(), 1)
        self.assertEqual(person.account_set.all()[0].date_deleted, None)
        luser = self._datastore._accounts().get(uid='kgtestuser3')
        self.assertEqual(luser.givenName, 'Test')

        response = self.client.get(reverse('kg_person_delete', args=[person.username]))
        self.failUnlessEqual(response.status_code, 200)
        # Test deleting
        response = self.client.post(reverse('kg_person_delete', args=[person.username]))
        self.failUnlessEqual(response.status_code, 302)
        
        person = Person.objects.get(username='kgtestuser3')

        self.assertEqual(person.is_active, False)
        self.assertEqual(person.projects.count(), 0)
        self.assertEqual(person.account_set.count(), 1)
        self.assertEqual(person.account_set.all()[0].date_deleted, datetime.date.today())
        self.failUnlessRaises(self._datastore._account.DoesNotExist, self._datastore._accounts().get, uid='kgtestuser3')

        # Test activating
        response = self.client.post(reverse('kg_person_activate', args=[person.username]))
        self.failUnlessEqual(response.status_code, 302)
        person = Person.objects.get(username='kgtestuser3')
        self.assertEqual(person.is_active, True)

    def stest_delete_account(self):
        person = Person.objects.get(pk=Person.objects.count())
        ua = person.account_set.all()[0]
        self.assertEqual(person.is_active, True)
        self.assertEqual(person.account_set.count(), 1)
        self.assertEqual(ua.date_deleted, None)

        response = self.client.post('/%susers/accounts/delete/%i/' % (settings.BASE_URL, ua.id))
        self.failUnlessEqual(response.status_code, 302)
        
        person = Person.objects.get(pk=Person.objects.count())
        ua = person.account_set.all()[0]
        self.assertEqual(ua.date_deleted, datetime.date.today())
        self.assertEqual(person.project_set.count(), 0)

    def stest_default_projects(self):

        person = Person.objects.get(pk=Person.objects.count())
        ua = person.account_set.all()[0]

        self.assertEqual(person.project_set.count(), 1)
        self.assertEqual(person.project_set.all()[0], ua.default_project)
        project = Project.objects.create(
            pid='test2',
            name='test project',
            leader=person,
            start_date = datetime.date.today(),
            machine_category=MachineCategory.objects.get(name='VPAC'),
            institute=Institute.objects.get(name='VPAC'),
            is_active=True,
            is_approved=True,
        )
        project.users.add(person)
        self.assertEqual(person.project_set.count(), 2)
        # change default
        response = self.client.post(reverse('kg_account_set_default', args=[ua.id, project.pid]))
        
        self.failUnlessEqual(response.status_code, 302)

        person = Person.objects.get(pk=Person.objects.count())
        ua = person.account_set.all()[0]
        project = Project.objects.get(pid='test2')
       
        self.assertEqual(person.project_set.count(), 2)
        self.assertEqual(project, ua.default_project)

       
    def stest_add_user_to_project(self):

        person = Person.objects.get(pk=Person.objects.count())
        person.account_set.all()[0]

        self.assertEqual(person.project_set.count(), 1)

        Project.objects.create(
            pid='test2',
            name='test project 5',
            leader=Person.objects.get(username='leader'),
            start_date = datetime.date.today(),
            machine_category=MachineCategory.objects.get(name='VPAC'),
            institute=Institute.objects.get(name='VPAC'),
            is_active=True,
            is_approved=True,
        )

        response = self.client.post(reverse('kg_person_detail', args=[person.username]), { 'project': 'test2', 'project-add': 'true' })
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(person.project_set.count(), 2)
