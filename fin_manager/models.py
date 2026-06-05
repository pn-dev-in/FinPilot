from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum, Avg
from decimal import Decimal
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import uuid


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserProfile(TimeStampedModel):
    CURRENCY_CHOICES = [
        ('INR', '₹ Indian Rupee'),
        ('USD', '$ US Dollar'),
        ('EUR', '€ Euro'),
        ('GBP', '£ British Pound'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='INR')
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    avatar_initial = models.CharField(max_length=2, default='FP')
    
      # Add these Groq AI Settings fields
    groq_api_key = models.TextField(blank=True, null=True)
    groq_enabled = models.BooleanField(default=False)
    groq_model = models.CharField(
        max_length=50, 
        default='llama3-70b-8192',
        choices=[
            ('llama3-70b-8192', 'Llama 3 70B (Most powerful - Recommended)'),
            ('llama3-8b-8192', 'Llama 3 8B (Fastest)'),
            ('mixtral-8x7b-32768', 'Mixtral 8x7B (Long context)'),
            ('gemma2-9b-it', 'Gemma 2 9B (Google)'),
        ]
    )
    
    def get_groq_api_key(self):
        """Return the Groq API key (user or system)"""
        if self.groq_api_key:
            return self.groq_api_key
        from django.conf import settings
        return getattr(settings, 'GROQ_API_KEY', None)

    def __str__(self):
        return f'{self.user.username} Profile'

    def get_currency_symbol(self):
        symbols = {'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£'}
        return symbols.get(self.currency, '₹')
    

class Account(TimeStampedModel):
    ACCOUNT_TYPES = [
        ('bank', 'Bank Account'),
        ('cash', 'Cash Wallet'),
        ('credit', 'Credit Card'),
        ('savings', 'Savings Account'),
        ('investment', 'Investment'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='bank')
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    is_active = models.BooleanField(default=True)
    color = models.CharField(max_length=7, default='#1D9E75')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.user.username})'

    @property
    def balance(self):
        income = self.transactions.filter(
            transaction_type='income'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        expense = self.transactions.filter(
            transaction_type='expense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        return self.initial_balance + income - expense


class Category(TimeStampedModel):
    CATEGORY_TYPES = [('income', 'Income'), ('expense', 'Expense'), ('both', 'Both')]
    ICONS = [
        ('food', 'Food & Dining'),
        ('transport', 'Transport'),
        ('housing', 'Housing & Rent'),
        ('health', 'Health'),
        ('entertainment', 'Entertainment'),
        ('shopping', 'Shopping'),
        ('education', 'Education'),
        ('subscriptions', 'Subscriptions'),
        ('utilities', 'Utilities'),
        ('salary', 'Salary'),
        ('freelance', 'Freelance'),
        ('investment', 'Investment'),
        ('transfer', 'Transfer'),
        ('other', 'Other'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories', null=True, blank=True)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=30, choices=ICONS, default='other')
    color = models.CharField(max_length=7, default='#1D9E75')
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES, default='expense')
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Transaction(TimeStampedModel):
    TRANSACTION_TYPES = [('income', 'Income'), ('expense', 'Expense'), ('transfer', 'Transfer')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    date = models.DateField(db_index=True)
    notes = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=False)
    ai_categorised = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'transaction_type']),
            models.Index(fields=['user', 'category']),
        ]

    def __str__(self):
        return f'{self.transaction_type}: {self.amount} — {self.description}'


class RecurringRule(TimeStampedModel):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_rules')
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    transaction_type = models.CharField(max_length=10, choices=Transaction.TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_due = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.description} ({self.frequency})'

    def advance_next_due(self):
        if self.frequency == 'daily':
            self.next_due = self.next_due + relativedelta(days=1)
        elif self.frequency == 'weekly':
            self.next_due = self.next_due + relativedelta(weeks=1)
        elif self.frequency == 'monthly':
            self.next_due = self.next_due + relativedelta(months=1)
        elif self.frequency == 'yearly':
            self.next_due = self.next_due + relativedelta(years=1)
        self.save()


class Budget(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    month = models.DateField()  # store as first day of month
    limit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    alert_threshold = models.IntegerField(default=80)  # alert at 80% usage

    class Meta:
        unique_together = ('user', 'category', 'month')
        ordering = ['-month']

    def __str__(self):
        return f'{self.category.name} budget — {self.month.strftime("%b %Y")}'

    @property
    def spent(self):
        return self.category.transactions.filter(
            user=self.user,
            transaction_type='expense',
            date__year=self.month.year,
            date__month=self.month.month,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    @property
    def percent_used(self):
        if self.limit_amount == 0:
            return 0
        return round(float(self.spent / self.limit_amount * 100), 1)

    @property
    def remaining(self):
        return self.limit_amount - self.spent

    @property
    def is_over_budget(self):
        return self.spent > self.limit_amount

    @property
    def is_near_limit(self):
        return self.percent_used >= self.alert_threshold


class Liability(TimeStampedModel):
    LIABILITY_TYPES = [('emi', 'EMI / Loan'), ('credit_card', 'Credit Card'), ('personal', 'Personal Loan'), ('one_time', 'One-time Payment')]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liabilities')
    name = models.CharField(max_length=100)
    liability_type = models.CharField(max_length=20, choices=LIABILITY_TYPES, default='emi')
    principal = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_long_term = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def monthly_payment(self):
        if not self.is_long_term or not self.end_date:
            return self.principal
        if self.interest_rate == 0:
            months = ((self.end_date.year - self.start_date.year) * 12
                      + self.end_date.month - self.start_date.month) or 1
            return round(self.principal / months, 2)
        months = ((self.end_date.year - date.today().year) * 12
                  + self.end_date.month - date.today().month)
        if months <= 0:
            return Decimal('0')
        monthly_rate = self.interest_rate / 12 / 100
        payment = (self.principal * monthly_rate) / (1 - (1 + monthly_rate) ** -months)
        return round(payment, 2)


class SavingsGoal(TimeStampedModel):
    PRIORITY_CHOICES = [
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='savings_goals')
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')  
    deadline = models.DateField(null=True, blank=True)
    icon = models.CharField(max_length=30, default='target')
    color = models.CharField(max_length=7, default='#1D9E75')
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateField(null=True, blank=True)  

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def percent_complete(self):
        if self.target_amount == 0:
            return 0
        return round(float(self.current_amount / self.target_amount * 100), 1)

    @property
    def remaining_amount(self):
        return self.target_amount - self.current_amount

    @property
    def months_to_deadline(self):
        if not self.deadline:
            return None
        delta = relativedelta(self.deadline, date.today())
        return max(delta.months + delta.years * 12, 0)

    @property
    def monthly_required(self):
        months = self.months_to_deadline
        if not months or months == 0:
            return self.remaining_amount
        return round(self.remaining_amount / months, 2)


class AIInsight(TimeStampedModel):
    INSIGHT_TYPES = [
        ('trend', 'Spending Trend'),
        ('anomaly', 'Anomaly Detected'),
        ('saving', 'Savings Opportunity'),
        ('budget', 'Budget Alert'),
        ('forecast', 'Forecast'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_insights')
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPES, default='trend')
    title = models.CharField(max_length=200)
    body = models.TextField()
    change_percent = models.FloatField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f'{self.insight_type}: {self.title}'
