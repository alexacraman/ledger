import datetime
from django.db.models import QuerySet
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase, Client
from .forms import TaskModelForm
from .models import Task

class TaskCreateTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='alex', password='password')
        self.client.force_login(self.user)

    def test_create_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('tasks:task-create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tasks/task_form.html')
        self.assertIsInstance(response.context['form'], TaskModelForm)
        form = response.context.get('form')
        self.assertIsNotNone(form, 'NO Form')

    def test_create_post(self):
        form_data = {
            'title': 'New task',
            'slug': 'new-task',
            'description': 'task tester',
            'complete': False,

        }
        self.client.force_login(self.user)
        response = self.client.post(reverse('tasks:task-create'), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('tasks:tasks'))

class TaskListTestView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(self.user)


    def get_list_view_response(self):
        url = reverse('tasks:tasks')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,'tasks/task_list.html')
        self.assertIsNotNone(response)
        self.assertIsInstance(response, list)

    def test_get_context_data(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('tasks:tasks'))
        self.assertEqual(response.status_code, 200)

        context = response.context
        self.assertIn('count', context)
        self.assertIn('ended', context)
        self.assertIn('now', context)
        self.assertIn('bookings', context)

        count = context['count']
        ended = context['ended']
        now   = context ['now']
        bookings = context['bookings']
        today = datetime.date
        self.assertIsInstance(count, int)
        self.assertIsInstance(ended, int)
        self.assertIsInstance(now, today)
        self.assertIsInstance(bookings, QuerySet)

class TestDetailView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(self.user)
        self.task = Task.objects.create(title='Task', slug='task-slug', description='task tester', complete=False)

    def get_detail_view_response(self):
        response = self.client.get(reverse('tasks:task-detail', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tasks/task_detail.html')
        self.assertContains(response, 'task tester')


class TestUpdateView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_login(self.user)
        self.task = Task.objects.create(title='Task', slug='task-slug', description='task tester', complete=False)

    def get_update_view_response(self):
        response = self.client.get(reverse('tasks:task-update', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tasks/task_form.html')
        self.assertContains(response, 'task tester')

        form_data = {
            'title':'Task Updated'
        }
        response = self.client.post(reverse('tasks:task-update', kwargs={'pk': self.task.pk}), data=form_data)
        self.assertEqual(response.status_code, 200)

        updated_model = Task.objects.get(pk=self.task.pk)
        self.assertEqual(updated_model.title, 'Task Updated')




