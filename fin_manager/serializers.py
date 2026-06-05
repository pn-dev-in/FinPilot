from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    UserProfile, Account, Category, Transaction,
    Budget, Liability, SavingsGoal, AIInsight, RecurringRule
)


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        UserProfile.objects.create(
            user=user,
            avatar_initial=(validated_data.get('first_name', 'F')[:1] +
                           validated_data.get('last_name', 'P')[:1]).upper() or 'FP'
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['currency', 'monthly_income', 'timezone', 'avatar_initial']


class AccountSerializer(serializers.ModelSerializer):
    balance = serializers.ReadOnlyField()

    class Meta:
        model = Account
        fields = ['id', 'name', 'account_type', 'initial_balance', 'balance', 'color', 'is_active']
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'color', 'category_type', 'is_system']
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'account', 'account_name', 'category', 'category_name',
            'category_icon', 'category_color', 'transaction_type',
            'amount', 'description', 'date', 'notes', 'is_recurring', 'ai_categorised'
        ]
        read_only_fields = ['id', 'ai_categorised']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def validate_account(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Account does not belong to you.")
        return value


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_color = serializers.CharField(source='category.color', read_only=True)
    spent = serializers.ReadOnlyField()
    percent_used = serializers.ReadOnlyField()
    remaining = serializers.ReadOnlyField()
    is_over_budget = serializers.ReadOnlyField()
    is_near_limit = serializers.ReadOnlyField()

    class Meta:
        model = Budget
        fields = [
            'id', 'category', 'category_name', 'category_color',
            'month', 'limit_amount', 'alert_threshold',
            'spent', 'percent_used', 'remaining', 'is_over_budget', 'is_near_limit'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class LiabilitySerializer(serializers.ModelSerializer):
    monthly_payment = serializers.ReadOnlyField()

    class Meta:
        model = Liability
        fields = [
            'id', 'name', 'liability_type', 'principal', 'interest_rate',
            'start_date', 'end_date', 'is_long_term', 'is_active', 'monthly_payment'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SavingsGoalSerializer(serializers.ModelSerializer):
    percent_complete = serializers.ReadOnlyField()
    remaining_amount = serializers.ReadOnlyField()
    monthly_required = serializers.ReadOnlyField()

    class Meta:
        model = SavingsGoal
        fields = [
            'id', 'name', 'target_amount', 'current_amount', 'deadline',
            'icon', 'color', 'is_completed',
            'percent_complete', 'remaining_amount', 'monthly_required'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AIInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIInsight
        fields = ['id', 'insight_type', 'title', 'body', 'change_percent', 'is_read', 'generated_at']
        read_only_fields = ['id', 'generated_at']


class RecurringRuleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = RecurringRule
        fields = [
            'id', 'account', 'category', 'category_name', 'transaction_type',
            'amount', 'description', 'frequency', 'start_date', 'end_date',
            'next_due', 'is_active'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class NaturalLanguageInputSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=500)
    account_id = serializers.UUIDField()
