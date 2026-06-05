"""
FinPilot Test Suite
Covers: models, services, API endpoints, views
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
from datetime import date, timedelta

from .models import (
    UserProfile, Account, Category, Transaction,
    Budget, Liability, SavingsGoal, AIInsight
)
from .services import DashboardService


# ─── Helpers ───────────────────────────────────────────────────────────────

def make_user(username='testuser', password='testpass123'):
    user = User.objects.create_user(username=username, password=password, email=f'{username}@test.com')
    UserProfile.objects.create(user=user)
    return user


def make_account(user, name='Test Account', balance=Decimal('10000')):
    return Account.objects.create(
        user=user, name=name, account_type='bank',
        initial_balance=balance, color='#1D9E75'
    )


def make_category(user, name='Food', cat_type='expense', icon='food', color='#D85A30'):
    return Category.objects.create(
        user=user, name=name, category_type=cat_type,
        icon=icon, color=color
    )


def make_transaction(user, account, category, tx_type='expense', amount=Decimal('500'), days_ago=0):
    return Transaction.objects.create(
        user=user, account=account, category=category,
        transaction_type=tx_type, amount=amount,
        description=f'Test {tx_type}',
        date=date.today() - timedelta(days=days_ago),
    )


# ─── Model Tests ────────────────────────────────────────────────────────────

class AccountModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.account = make_account(self.user, balance=Decimal('5000'))
        self.cat = make_category(self.user)

    def test_balance_with_no_transactions(self):
        self.assertEqual(self.account.balance, Decimal('5000'))

    def test_balance_adds_income(self):
        income_cat = make_category(self.user, 'Salary', 'income', 'salary', '#1D9E75')
        make_transaction(self.user, self.account, income_cat, 'income', Decimal('10000'))
        self.assertEqual(self.account.balance, Decimal('15000'))

    def test_balance_subtracts_expense(self):
        make_transaction(self.user, self.account, self.cat, 'expense', Decimal('1000'))
        self.assertEqual(self.account.balance, Decimal('4000'))

    def test_balance_with_both(self):
        income_cat = make_category(self.user, 'Salary', 'income', 'salary', '#1D9E75')
        make_transaction(self.user, self.account, income_cat, 'income', Decimal('5000'))
        make_transaction(self.user, self.account, self.cat, 'expense', Decimal('2000'))
        self.assertEqual(self.account.balance, Decimal('8000'))


class LiabilityModelTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_one_time_liability_monthly_payment(self):
        l = Liability.objects.create(
            user=self.user, name='Car repair',
            principal=Decimal('5000'),
            start_date=date.today(),
            is_long_term=False,
        )
        self.assertEqual(l.monthly_payment, Decimal('5000'))

    def test_zero_interest_emi(self):
        start = date.today().replace(day=1)
        end = (start + timedelta(days=366)).replace(day=1)  # ~12 months
        l = Liability.objects.create(
            user=self.user, name='Phone EMI',
            principal=Decimal('12000'),
            interest_rate=Decimal('0'),
            start_date=start,
            end_date=end,
            is_long_term=True,
        )
        # Should be roughly 1000/month
        self.assertGreater(l.monthly_payment, Decimal('0'))


class SavingsGoalTest(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_percent_complete(self):
        g = SavingsGoal.objects.create(
            user=self.user, name='Holiday',
            target_amount=Decimal('50000'),
            current_amount=Decimal('25000'),
        )
        self.assertEqual(g.percent_complete, 50.0)

    def test_remaining_amount(self):
        g = SavingsGoal.objects.create(
            user=self.user, name='Holiday',
            target_amount=Decimal('50000'),
            current_amount=Decimal('30000'),
        )
        self.assertEqual(g.remaining_amount, Decimal('20000'))

    def test_percent_complete_over_100(self):
        g = SavingsGoal.objects.create(
            user=self.user, name='Done',
            target_amount=Decimal('10000'),
            current_amount=Decimal('12000'),
        )
        self.assertEqual(g.percent_complete, 120.0)


class BudgetModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.account = make_account(self.user)
        self.cat = make_category(self.user, 'Food')
        today = date.today().replace(day=1)
        self.budget = Budget.objects.create(
            user=self.user, category=self.cat,
            month=today, limit_amount=Decimal('3000'),
            alert_threshold=80,
        )

    def test_spent_no_transactions(self):
        self.assertEqual(self.budget.spent, Decimal('0'))

    def test_percent_used(self):
        make_transaction(self.user, self.account, self.cat, 'expense', Decimal('1500'))
        self.assertEqual(self.budget.percent_used, 50.0)

    def test_is_over_budget(self):
        make_transaction(self.user, self.account, self.cat, 'expense', Decimal('4000'))
        self.assertTrue(self.budget.is_over_budget)

    def test_is_near_limit(self):
        make_transaction(self.user, self.account, self.cat, 'expense', Decimal('2500'))
        self.assertTrue(self.budget.is_near_limit)  # 83% > 80%


# ─── Service Tests ──────────────────────────────────────────────────────────

class DashboardServiceTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.account = make_account(self.user)
        self.income_cat = make_category(self.user, 'Salary', 'income', 'salary', '#1D9E75')
        self.expense_cat = make_category(self.user, 'Food', 'expense', 'food', '#D85A30')
        self.service = DashboardService(self.user)

    def test_monthly_income_empty(self):
        self.assertEqual(self.service.get_monthly_income(), Decimal('0'))

    def test_monthly_income(self):
        make_transaction(self.user, self.account, self.income_cat, 'income', Decimal('50000'))
        self.assertEqual(self.service.get_monthly_income(), Decimal('50000'))

    def test_monthly_expense(self):
        make_transaction(self.user, self.account, self.expense_cat, 'expense', Decimal('5000'))
        self.assertEqual(self.service.get_monthly_expense(), Decimal('5000'))

    def test_net_savings(self):
        make_transaction(self.user, self.account, self.income_cat, 'income', Decimal('50000'))
        make_transaction(self.user, self.account, self.expense_cat, 'expense', Decimal('20000'))
        self.assertEqual(self.service.get_net_savings(), Decimal('30000'))

    def test_health_score_range(self):
        score = self.service.get_financial_health_score()
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_health_score_excellent_when_good_savings(self):
        make_transaction(self.user, self.account, self.income_cat, 'income', Decimal('50000'))
        make_transaction(self.user, self.account, self.expense_cat, 'expense', Decimal('10000'))
        score = self.service.get_financial_health_score()
        self.assertGreater(score, 60)

    def test_total_balance(self):
        balance = self.service.get_total_balance()
        self.assertEqual(balance, Decimal('10000'))

    def test_monthly_trend_returns_correct_months(self):
        trend = self.service.get_monthly_trend(3)
        self.assertEqual(len(trend), 3)
        self.assertIn('month', trend[0])
        self.assertIn('income', trend[0])
        self.assertIn('expense', trend[0])


# ─── View Tests ─────────────────────────────────────────────────────────────

class ViewAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()

    def test_landing_page_accessible(self):
        r = self.client.get(reverse('landing'))
        self.assertEqual(r.status_code, 200)

    def test_dashboard_redirects_unauthenticated(self):
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r['Location'])

    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username='testuser', password='testpass123')
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)

    def test_register_get(self):
        r = self.client.get(reverse('register'))
        self.assertEqual(r.status_code, 200)

    def test_register_creates_user(self):
        r = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@test.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'complexpass99!',
            'password2': 'complexpass99!',
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_add_transaction(self):
        self.client.login(username='testuser', password='testpass123')
        account = make_account(self.user)
        cat = make_category(self.user)
        r = self.client.post(reverse('transactions'), {
            'account': account.id,
            'category': cat.id,
            'transaction_type': 'expense',
            'amount': '500.00',
            'description': 'Lunch',
            'date': date.today().isoformat(),
            'notes': '',
            'is_recurring': False,
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Transaction.objects.filter(description='Lunch').exists())


# ─── API Tests ───────────────────────────────────────────────────────────────

class APIAuthTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user('apiuser', 'apipass123!')

    def get_token(self):
        refresh = RefreshToken.for_user(self.user)
        return str(refresh.access_token)

    def auth(self):
        token = self.get_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_unauthenticated_dashboard_returns_401(self):
        r = self.client.get('/api/dashboard/')
        self.assertEqual(r.status_code, 401)

    def test_dashboard_returns_200_when_authed(self):
        self.auth()
        r = self.client.get('/api/dashboard/')
        self.assertEqual(r.status_code, 200)

    def test_dashboard_has_required_fields(self):
        self.auth()
        r = self.client.get('/api/dashboard/')
        data = r.json()
        for key in ['balance', 'income', 'expense', 'savings', 'health_score']:
            self.assertIn(key, data)

    def test_create_account(self):
        self.auth()
        r = self.client.post('/api/accounts/', {
            'name': 'HDFC Savings',
            'account_type': 'bank',
            'initial_balance': '25000.00',
            'color': '#1D9E75',
        })
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['name'], 'HDFC Savings')

    def test_create_transaction(self):
        self.auth()
        account = make_account(self.user)
        cat = make_category(self.user)
        r = self.client.post('/api/transactions/', {
            'account': str(account.id),
            'category': str(cat.id),
            'transaction_type': 'expense',
            'amount': '1200.00',
            'description': 'Grocery',
            'date': date.today().isoformat(),
        })
        self.assertEqual(r.status_code, 201)

    def test_transaction_filters_by_type(self):
        self.auth()
        account = make_account(self.user)
        income_cat = make_category(self.user, 'Salary', 'income', 'salary', '#1D9E75')
        expense_cat = make_category(self.user, 'Food', 'expense', 'food', '#D85A30')
        make_transaction(self.user, account, income_cat, 'income', Decimal('50000'))
        make_transaction(self.user, account, expense_cat, 'expense', Decimal('2000'))

        r = self.client.get('/api/transactions/?transaction_type=income')
        self.assertEqual(r.status_code, 200)
        results = r.json()['results']
        self.assertTrue(all(t['transaction_type'] == 'income' for t in results))

    def test_create_budget(self):
        self.auth()
        cat = make_category(self.user)
        r = self.client.post('/api/budgets/', {
            'category': str(cat.id),
            'month': date.today().replace(day=1).isoformat(),
            'limit_amount': '5000.00',
            'alert_threshold': 80,
        })
        self.assertEqual(r.status_code, 201)

    def test_create_savings_goal(self):
        self.auth()
        r = self.client.post('/api/goals/', {
            'name': 'Emergency Fund',
            'target_amount': '100000.00',
            'current_amount': '10000.00',
            'color': '#1D9E75',
        })
        self.assertEqual(r.status_code, 201)

    def test_add_funds_to_goal(self):
        self.auth()
        goal = SavingsGoal.objects.create(
            user=self.user, name='Car',
            target_amount=Decimal('500000'),
            current_amount=Decimal('100000'),
        )
        r = self.client.post(f'/api/goals/{goal.id}/add_funds/', {'amount': '50000'})
        self.assertEqual(r.status_code, 200)
        goal.refresh_from_db()
        self.assertEqual(goal.current_amount, Decimal('150000'))

    def test_registration_api(self):
        r = self.client.post('/api/auth/register/', {
            'username': 'newapi',
            'email': 'newapi@test.com',
            'first_name': 'New',
            'last_name': 'API',
            'password': 'complexpass99!',
            'password2': 'complexpass99!',
        })
        self.assertEqual(r.status_code, 201)
        self.assertTrue(User.objects.filter(username='newapi').exists())

    def test_jwt_token_obtain(self):
        r = self.client.post('/api/auth/token/', {
            'username': 'apiuser',
            'password': 'apipass123!',
        })
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.json())
        self.assertIn('refresh', r.json())

    def test_report_summary(self):
        self.auth()
        r = self.client.get('/api/reports/summary/')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn('trend', data)
        self.assertIn('health_score', data)
