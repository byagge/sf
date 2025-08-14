from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Defect, DefectRepairTask
from apps.products.models import Product
from apps.operations.workshops.models import Workshop

User = get_user_model()

class DefectModelTest(TestCase):
    def setUp(self):
        # Создаем тестовые данные
        self.workshop = Workshop.objects.create(name="Тестовый цех")
        self.master = User.objects.create_user(
            username='master',
            password='testpass123',
            role='master',
            workshop=self.workshop
        )
        self.worker = User.objects.create_user(
            username='worker',
            password='testpass123',
            role='worker',
            workshop=self.workshop
        )
        self.product = Product.objects.create(name="Тестовый продукт")
        
    def test_defect_creation(self):
        """Тест создания брака"""
        defect = Defect.objects.create(
            product=self.product,
            user=self.worker
        )
        
        self.assertEqual(defect.status, Defect.DefectStatus.PENDING_MASTER_REVIEW)
        self.assertIsNone(defect.defect_type)
        self.assertIsNone(defect.can_be_fixed)
        self.assertEqual(defect.get_workshop(), self.workshop)
        
    def test_master_confirmation(self):
        """Тест подтверждения брака мастером"""
        defect = Defect.objects.create(
            product=self.product,
            user=self.worker
        )
        
        # Мастер подтверждает брак
        defect.confirm_by_master(self.master)
        
        self.assertEqual(defect.status, Defect.DefectStatus.MASTER_CONFIRMED)
        self.assertEqual(defect.master_confirmed_by, self.master)
        self.assertIsNotNone(defect.master_confirmed_at)
        
    def test_set_repairability(self):
        """Тест установки возможности восстановления"""
        defect = Defect.objects.create(
            product=self.product,
            user=self.worker
        )
        
        # Устанавливаем, что брак можно починить
        defect.set_repairability(True)
        self.assertTrue(defect.can_be_fixed)
        self.assertEqual(defect.status, Defect.DefectStatus.CAN_BE_FIXED)
        
        # Устанавливаем, что брак нельзя починить
        defect.set_repairability(False)
        self.assertFalse(defect.can_be_fixed)
        self.assertEqual(defect.status, Defect.DefectStatus.UNREPAIRABLE)
        
    def test_set_defect_type(self):
        """Тест установки типа брака"""
        defect = Defect.objects.create(
            product=self.product,
            user=self.worker
        )
        
        defect.set_defect_type(Defect.DefectType.TECHNICAL)
        self.assertEqual(defect.defect_type, Defect.DefectType.TECHNICAL)
        
        defect.set_defect_type(Defect.DefectType.MANUAL)
        self.assertEqual(defect.defect_type, Defect.DefectType.MANUAL)
        
    def test_send_to_workshop(self):
        """Тест отправки брака в цех"""
        defect = Defect.objects.create(
            product=self.product,
            user=self.worker
        )
        
        target_workshop = Workshop.objects.create(name="Цех восстановления")
        defect.send_to_workshop(target_workshop)
        
        self.assertEqual(defect.target_workshop, target_workshop)
        self.assertEqual(defect.status, Defect.DefectStatus.SENT_TO_WORKSHOP)
        
    def test_mark_as_fixed(self):
        """Тест отметки брака как исправленного"""
        defect = Defect.objects.create(
            product=self.product,
            user=self.worker
        )
        
        defect.mark_as_fixed(self.worker)
        
        self.assertEqual(defect.status, Defect.DefectStatus.FIXED)
        self.assertEqual(defect.fixed_by, self.worker)
        self.assertIsNotNone(defect.fixed_at)
        
    def test_master_permissions(self):
        """Тест прав мастера"""
        defect = Defect.objects.create(
            product=self.product,
            user=self.worker
        )
        
        # Мастер может проверить брак своего цеха
        self.assertTrue(defect.can_master_review(self.master))
        
        # Мастер другого цеха не может проверить
        other_workshop = Workshop.objects.create(name="Другой цех")
        other_master = User.objects.create_user(
            username='other_master',
            password='testpass123',
            role='master',
            workshop=other_workshop
        )
        self.assertFalse(defect.can_master_review(other_master))


class DefectRepairTaskModelTest(TestCase):
    def setUp(self):
        self.workshop = Workshop.objects.create(name="Тестовый цех")
        self.worker = User.objects.create_user(
            username='worker',
            password='testpass123',
            role='worker',
            workshop=self.workshop
        )
        self.product = Product.objects.create(name="Тестовый продукт")
        self.defect = Defect.objects.create(
            product=self.product,
            user=self.worker
        )
        
    def test_task_creation(self):
        """Тест создания задачи по восстановлению"""
        task = DefectRepairTask.objects.create(
            defect=self.defect,
            workshop=self.workshop,
            title="Восстановление брака"
        )
        
        self.assertEqual(task.status, DefectRepairTask.TaskStatus.PENDING)
        self.assertEqual(task.workshop, self.workshop)
        self.assertEqual(task.defect, self.defect)
        
    def test_auto_title_generation(self):
        """Тест автоматической генерации названия задачи"""
        task = DefectRepairTask.objects.create(
            defect=self.defect,
            workshop=self.workshop
        )
        
        self.assertIn("Восстановление брака", task.title)
        
    def test_task_workflow(self):
        """Тест рабочего процесса задачи"""
        task = DefectRepairTask.objects.create(
            defect=self.defect,
            workshop=self.workshop,
            title="Восстановление брака"
        )
        
        # Начинаем работу
        task.start_work()
        self.assertEqual(task.status, DefectRepairTask.TaskStatus.IN_PROGRESS)
        self.assertIsNotNone(task.started_at)
        
        # Завершаем задачу
        task.complete_task()
        self.assertEqual(task.status, DefectRepairTask.TaskStatus.COMPLETED)
        self.assertIsNotNone(task.completed_at)
        
        # Проверяем, что брак отмечен как исправленный
        self.assertEqual(self.defect.status, Defect.DefectStatus.FIXED)
        self.assertEqual(self.defect.fixed_by, task.assigned_to)


class DefectAPITest(APITestCase):
    def setUp(self):
        self.client = Client()
        self.workshop = Workshop.objects.create(name="Тестовый цех")
        self.master = User.objects.create_user(
            username='master',
            password='testpass123',
            role='master',
            workshop=self.workshop
        )
        self.worker = User.objects.create_user(
            username='worker',
            password='testpass123',
            role='worker',
            workshop=self.workshop
        )
        self.product = Product.objects.create(name="Тестовый продукт")
        self.defect = Defect.objects.create(
            product=self.product,
            user=self.worker
        )
        
    def test_defect_list_api(self):
        """Тест API списка браков"""
        self.client.force_login(self.master)
        url = reverse('defect-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
    def test_defect_detail_api(self):
        """Тест API деталей брака"""
        self.client.force_login(self.master)
        url = reverse('defect-detail', args=[self.defect.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.defect.id)
        
    def test_master_confirmation_api(self):
        """Тест API подтверждения мастером"""
        self.client.force_login(self.master)
        url = reverse('defect-confirm-by-master', args=[self.defect.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что брак подтвержден
        self.defect.refresh_from_db()
        self.assertEqual(self.defect.status, Defect.DefectStatus.MASTER_CONFIRMED)
        self.assertEqual(self.defect.master_confirmed_by, self.master)
        
    def test_defect_review_api(self):
        """Тест API полной проверки брака"""
        self.client.force_login(self.master)
        url = reverse('defect-review-defect', args=[self.defect.id])
        
        # Тестируем случай, когда брак можно починить
        data = {
            'can_be_fixed': True,
            'target_workshop_id': self.workshop.id
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что брак отправлен в цех
        self.defect.refresh_from_db()
        self.assertEqual(self.defect.status, Defect.DefectStatus.SENT_TO_WORKSHOP)
        self.assertEqual(self.defect.target_workshop, self.workshop)
        
        # Проверяем, что создана задача по восстановлению
        self.assertTrue(hasattr(self.defect, 'repair_task'))
        
    def test_defect_review_unrepairable_api(self):
        """Тест API проверки невосстанавливаемого брака"""
        self.client.force_login(self.master)
        url = reverse('defect-review-defect', args=[self.defect.id])
        
        # Тестируем случай, когда брак нельзя починить
        data = {
            'can_be_fixed': False,
            'defect_type': Defect.DefectType.TECHNICAL
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что брак отмечен как невосстанавливаемый
        self.defect.refresh_from_db()
        self.assertEqual(self.defect.status, Defect.DefectStatus.UNREPAIRABLE)
        self.assertEqual(self.defect.defect_type, Defect.DefectType.TECHNICAL)
        
    def test_mark_as_fixed_api(self):
        """Тест API отметки как исправленного"""
        # Сначала отправляем брак в цех
        self.defect.send_to_workshop(self.workshop)
        
        self.client.force_login(self.worker)
        url = reverse('defect-mark-as-fixed', args=[self.defect.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что брак отмечен как исправленный
        self.defect.refresh_from_db()
        self.assertEqual(self.defect.status, Defect.DefectStatus.FIXED)
        self.assertEqual(self.defect.fixed_by, self.worker)


class DefectRepairTaskAPITest(APITestCase):
    def setUp(self):
        self.client = Client()
        self.workshop = Workshop.objects.create(name="Тестовый цех")
        self.worker = User.objects.create_user(
            username='worker',
            password='testpass123',
            role='worker',
            workshop=self.workshop
        )
        self.product = Product.objects.create(name="Тестовый продукт")
        self.defect = Defect.objects.create(
            product=self.product,
            user=self.worker
        )
        self.task = DefectRepairTask.objects.create(
            defect=self.defect,
            workshop=self.workshop,
            title="Восстановление брака"
        )
        
    def test_repair_task_list_api(self):
        """Тест API списка задач по восстановлению"""
        self.client.force_login(self.worker)
        url = reverse('defect-repair-task-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
    def test_repair_task_detail_api(self):
        """Тест API деталей задачи по восстановлению"""
        self.client.force_login(self.worker)
        url = reverse('defect-repair-task-detail', args=[self.task.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.task.id)
        
    def test_start_work_api(self):
        """Тест API начала работы над задачей"""
        self.client.force_login(self.worker)
        url = reverse('defect-repair-task-start-work', args=[self.task.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что задача начата
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, DefectRepairTask.TaskStatus.IN_PROGRESS)
        self.assertIsNotNone(self.task.started_at)
        
    def test_complete_task_api(self):
        """Тест API завершения задачи"""
        self.client.force_login(self.worker)
        url = reverse('defect-repair-task-complete-task', args=[self.task.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что задача завершена
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, DefectRepairTask.TaskStatus.COMPLETED)
        self.assertIsNotNone(self.task.completed_at)
        
        # Проверяем, что брак отмечен как исправленный
        self.defect.refresh_from_db()
        self.assertEqual(self.defect.status, Defect.DefectStatus.FIXED)


class DefectIntegrationTest(TestCase):
    """Интеграционные тесты для полного процесса работы с браком"""
    
    def setUp(self):
        self.workshop = Workshop.objects.create(name="Тестовый цех")
        self.master = User.objects.create_user(
            username='master',
            password='testpass123',
            role='master',
            workshop=self.workshop
        )
        self.worker = User.objects.create_user(
            username='worker',
            password='testpass123',
            role='worker',
            workshop=self.workshop
        )
        self.product = Product.objects.create(name="Тестовый продукт")
        
    def test_complete_defect_workflow(self):
        """Тест полного процесса работы с браком"""
        # 1. Создаем брак
        defect = Defect.objects.create(
            product=self.product,
            user=self.worker
        )
        self.assertEqual(defect.status, Defect.DefectStatus.PENDING_MASTER_REVIEW)
        
        # 2. Мастер подтверждает брак
        defect.confirm_by_master(self.master)
        self.assertEqual(defect.status, Defect.DefectStatus.MASTER_CONFIRMED)
        
        # 3. Мастер определяет, что брак можно починить
        defect.set_repairability(True)
        self.assertEqual(defect.status, Defect.DefectStatus.CAN_BE_FIXED)
        
        # 4. Мастер отправляет брак в цех для восстановления
        defect.send_to_workshop(self.workshop)
        self.assertEqual(defect.status, Defect.DefectStatus.SENT_TO_WORKSHOP)
        
        # 5. Создается задача по восстановлению
        task = DefectRepairTask.objects.get(defect=defect)
        self.assertEqual(task.workshop, self.workshop)
        self.assertEqual(task.status, DefectRepairTask.TaskStatus.PENDING)
        
        # 6. Рабочий начинает работу
        task.start_work()
        self.assertEqual(task.status, DefectRepairTask.TaskStatus.IN_PROGRESS)
        
        # 7. Рабочий завершает задачу
        task.complete_task()
        self.assertEqual(task.status, DefectRepairTask.TaskStatus.COMPLETED)
        
        # 8. Брак отмечен как исправленный
        defect.refresh_from_db()
        self.assertEqual(defect.status, Defect.DefectStatus.FIXED)
        self.assertEqual(defect.fixed_by, task.assigned_to)
        
    def test_unrepairable_defect_workflow(self):
        """Тест процесса работы с невосстанавливаемым браком"""
        # 1. Создаем брак
        defect = Defect.objects.create(
            product=self.product,
            user=self.worker
        )
        
        # 2. Мастер подтверждает брак
        defect.confirm_by_master(self.master)
        
        # 3. Мастер определяет, что брак нельзя починить
        defect.set_repairability(False)
        
        # 4. Мастер устанавливает тип брака
        defect.set_defect_type(Defect.DefectType.MANUAL)
        
        # Проверяем финальное состояние
        self.assertEqual(defect.status, Defect.DefectStatus.UNREPAIRABLE)
        self.assertEqual(defect.defect_type, Defect.DefectType.MANUAL)
        self.assertFalse(defect.can_be_fixed)
        
        # Убеждаемся, что задача по восстановлению не создана
        self.assertFalse(hasattr(defect, 'repair_task')) 