from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Transaction, Budget, Liability, SavingsGoal, Account, UserProfile, Category


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=False)
    last_name = forms.CharField(max_length=50, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'fp-input'


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['account', 'category', 'transaction_type', 'amount', 'description', 'date', 'notes', 'is_recurring']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'fp-input'}),
            'amount': forms.NumberInput(attrs={'class': 'fp-input', 'step': '0.01', 'min': '0'}),
            'description': forms.TextInput(attrs={'class': 'fp-input'}),
            'notes': forms.Textarea(attrs={'class': 'fp-input', 'rows': 2}),
            'account': forms.Select(attrs={'class': 'fp-input'}),
            'category': forms.Select(attrs={'class': 'fp-input'}),
            'transaction_type': forms.Select(attrs={'class': 'fp-input'}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['account'].queryset = Account.objects.filter(user=user, is_active=True)
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(is_system=True)
            )
        self.fields['date'].initial = __import__('datetime').date.today()


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'limit_amount', 'alert_threshold']
        widgets = {
            'category': forms.Select(attrs={'class': 'fp-input'}),
            'limit_amount': forms.NumberInput(attrs={'class': 'fp-input', 'step': '0.01'}),
            'alert_threshold': forms.NumberInput(attrs={'class': 'fp-input', 'min': '1', 'max': '100'}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(is_system=True),
                category_type__in=['expense', 'both']
            )


class LiabilityForm(forms.ModelForm):
    class Meta:
        model = Liability
        fields = ['name', 'liability_type', 'principal', 'interest_rate', 'start_date', 'end_date', 'is_long_term']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'fp-input'}),
            'liability_type': forms.Select(attrs={'class': 'fp-input'}),
            'principal': forms.NumberInput(attrs={'class': 'fp-input', 'step': '0.01'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'fp-input', 'step': '0.01'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'fp-input'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'fp-input'}),
            'is_long_term': forms.CheckboxInput(attrs={'class': 'fp-checkbox'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_long_term = cleaned_data.get('is_long_term')
        if not is_long_term:
            cleaned_data['end_date'] = None
            cleaned_data['interest_rate'] = None
        return cleaned_data


class SavingsGoalForm(forms.ModelForm):
    class Meta:
        model = SavingsGoal
        fields = ['name', 'target_amount', 'current_amount', 'deadline', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'fp-input'}),
            'target_amount': forms.NumberInput(attrs={'class': 'fp-input', 'step': '0.01'}),
            'current_amount': forms.NumberInput(attrs={'class': 'fp-input', 'step': '0.01'}),
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'fp-input'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'fp-input'}),
        }


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'account_type', 'initial_balance', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'fp-input'}),
            'account_type': forms.Select(attrs={'class': 'fp-input'}),
            'initial_balance': forms.NumberInput(attrs={'class': 'fp-input', 'step': '0.01'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'fp-input'}),
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['currency', 'monthly_income', 'timezone']
        widgets = {
            'currency': forms.Select(attrs={'class': 'fp-input'}),
            'monthly_income': forms.NumberInput(attrs={'class': 'fp-input', 'step': '0.01'}),
            'timezone': forms.TextInput(attrs={'class': 'fp-input'}),
        }
