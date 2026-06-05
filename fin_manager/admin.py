from django.contrib import admin
from .models import (
    UserProfile, Account, Category, Transaction,
    Budget, Liability, SavingsGoal, AIInsight, RecurringRule
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'currency', 'monthly_income']

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'account_type', 'initial_balance']
    list_filter = ['account_type']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'category_type', 'is_system', 'user']
    list_filter = ['category_type', 'is_system']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['description', 'amount', 'transaction_type', 'date', 'user', 'category']
    list_filter = ['transaction_type', 'date']
    search_fields = ['description']
    date_hierarchy = 'date'

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['category', 'user', 'month', 'limit_amount']

@admin.register(Liability)
class LiabilityAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'principal', 'interest_rate', 'is_long_term']

@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'target_amount', 'current_amount', 'is_completed']

@admin.register(AIInsight)
class AIInsightAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'insight_type', 'is_read', 'generated_at']

@admin.register(RecurringRule)
class RecurringRuleAdmin(admin.ModelAdmin):
    list_display = ['description', 'user', 'frequency', 'next_due', 'is_active']
