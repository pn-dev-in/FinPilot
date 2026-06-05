from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Sum, Q
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.conf import settings
import json

from .models import (
    Account, Category, Transaction, Budget,
    Liability, SavingsGoal, UserProfile, AIInsight, RecurringRule
)
from .forms import (
    UserRegistrationForm, TransactionForm, BudgetForm,
    LiabilityForm, SavingsGoalForm, AccountForm, UserProfileForm
)
from .services import DashboardService, InsightService, BudgetPredictionService, GroqInsightService, TransactionService


def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'fin_manager/landing.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(
                user=user,
                avatar_initial=(
                    form.cleaned_data.get('first_name', 'F')[:1] +
                    form.cleaned_data.get('last_name', 'P')[:1]
                ).upper() or 'FP'
            )
            _create_default_data(user)
            login(request, user)
            messages.success(request, f'Welcome to FinPilot, {user.first_name or user.username}!')
            return redirect('dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def _create_default_data(user):
    """Seed system categories and a default bank account."""
    system_cats = [
        ('Food & Dining', 'food', '#D85A30', 'expense'),
        ('Transport', 'transport', '#378ADD', 'expense'),
        ('Housing & Rent', 'housing', '#7F77DD', 'expense'),
        ('Health', 'health', '#E24B4A', 'expense'),
        ('Entertainment', 'entertainment', '#D4537E', 'expense'),
        ('Shopping', 'shopping', '#BA7517', 'expense'),
        ('Education', 'education', '#185FA5', 'expense'),
        ('Subscriptions', 'subscriptions', '#533F8B', 'expense'),
        ('Utilities', 'utilities', '#888780', 'expense'),
        ('Salary', 'salary', '#1D9E75', 'income'),
        ('Freelance', 'freelance', '#0F6E56', 'income'),
        ('Investment Returns', 'investment', '#085041', 'income'),
        ('Other', 'other', '#5F5E5A', 'both'),
    ]
    for name, icon, color, cat_type in system_cats:
        Category.objects.get_or_create(
            user=user,
            name=name,
            defaults={'icon': icon, 'color': color, 'category_type': cat_type}
        )
    Account.objects.get_or_create(
        user=user,
        name='Primary Bank Account',
        defaults={'account_type': 'bank', 'initial_balance': Decimal('0'), 'color': '#1D9E75'}
    )


@login_required
def dashboard(request):
    service = DashboardService(request.user)
    context = service.get_full_context()

    UserProfile.objects.get_or_create(user=request.user)
    profile = request.user.profile

    context['profile'] = profile
    context['currency'] = profile.get_currency_symbol()
    context['goals'] = SavingsGoal.objects.filter(user=request.user, is_completed=False)[:3]
    context['liabilities'] = Liability.objects.filter(user=request.user, is_active=True)[:5]

    
    # Get unique AI insights - SQLite compatible (no DISTINCT ON)
    ai_insights_queryset = AIInsight.objects.filter(
        user=request.user, 
        is_read=False
    ).order_by('-generated_at')
    
    # Remove duplicates by title using Python (SQLite compatible)
    unique_insights = []
    seen_titles = set()
    for insight in ai_insights_queryset:
        if insight.title not in seen_titles:
            seen_titles.add(insight.title)
            unique_insights.append(insight)
        if len(unique_insights) >= 3:  # Limit to 3 insights
            break
    
    context['ai_insights'] = unique_insights


    income = context.get('income', 0)
    expense = context.get('expense', 0)
    savings = income - expense
    
    if income > 0:
        savings_rate = (savings / income) * 100
    else:
        savings_rate = 0
    
    context['savings'] = savings
    context['savings_rate'] = savings_rate

    context['trend_json'] = json.dumps(context['monthly_trend'])
    context['category_json'] = json.dumps([
        {
            'label': c['category__name'],
            'value': float(c['total']),
            'color': c['category__color'],
        }
        for c in context['expense_by_category']
    ])

    return render(request, 'fin_manager/dashboard.html', context)


@login_required
def transactions(request):
    qs = Transaction.objects.filter(
        user=request.user
    ).select_related('category', 'account')

    tx_type = request.GET.get('type', '')
    category_id = request.GET.get('category', '')
    month = request.GET.get('month', '')

    if tx_type:
        qs = qs.filter(transaction_type=tx_type)
    if category_id:
        qs = qs.filter(category_id=category_id)
    if month:
        year, m = month.split('-')
        qs = qs.filter(date__year=year, date__month=m)

    total_income = qs.filter(transaction_type='income').aggregate(t=Sum('amount'))['t'] or 0
    total_expense = qs.filter(transaction_type='expense').aggregate(t=Sum('amount'))['t'] or 0
    net_amount = total_income - total_expense

    categories = Category.objects.filter(
        Q(user=request.user) | Q(is_system=True)
    )
    form = TransactionForm(user=request.user)

    if request.method == 'POST':
        form = TransactionForm(request.user, request.POST)
        if form.is_valid():
            t = form.save(commit=False)
            t.user = request.user
            t.save()
            messages.success(request, 'Transaction added.')
            return redirect('transactions')

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'fin_manager/transactions.html', {
        'transactions': qs[:100],
        'form': form,
        'categories': categories,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_amount': net_amount,
        'currency': profile.get_currency_symbol(),
        'profile': profile,
    })


# Add these to your views.py if not already present

@login_required
def edit_budget(request, pk):
    budget = get_object_or_404(Budget, id=pk, user=request.user)
    
    if request.method == 'POST':
        category_id = request.POST.get('category')
        limit_amount = Decimal(request.POST.get('limit_amount'))
        alert_threshold = int(request.POST.get('alert_threshold', 80))
        
        budget.category_id = category_id
        budget.limit_amount = limit_amount
        budget.alert_threshold = alert_threshold
        budget.save()
        
        messages.success(request, f'Budget for "{budget.category.name}" updated successfully!')
        return redirect('budgets')
    
    return redirect('budgets')


@login_required
def delete_budget(request, pk):
    budget = get_object_or_404(Budget, id=pk, user=request.user)
    category_name = budget.category.name
    budget.delete()
    messages.success(request, f'Budget for "{category_name}" deleted successfully!')
    return redirect('budgets')


@login_required
def get_budget_json(request, pk):
    budget = get_object_or_404(Budget, id=pk, user=request.user)
    return JsonResponse({
        'id': str(budget.id),
        'category_id': str(budget.category.id),
        'category_name': budget.category.name,
        'limit_amount': float(budget.limit_amount),
        'alert_threshold': budget.alert_threshold,
        'spent': float(budget.spent),
        'percent_used': budget.percent_used,
        'remaining': float(budget.remaining),
        'is_over_budget': budget.is_over_budget,
        'is_near_limit': budget.is_near_limit,
    })

@login_required
def budgets(request):
    # Get month parameter
    month_param = request.GET.get('month')
    today = date.today()
    
    if month_param:
        try:
            year, month = map(int, month_param.split('-'))
            month_start = date(year, month, 1)
        except ValueError:
            month_start = today.replace(day=1)
    else:
        month_start = today.replace(day=1)
    
    # Get budgets for the month
    budget_list = Budget.objects.filter(
        user=request.user, month=month_start
    ).select_related('category')
    
    # Calculate summary stats
    total_budget = sum(float(b.limit_amount) for b in budget_list)
    total_spent = sum(float(b.spent) for b in budget_list)
    remaining_budget = total_budget - total_spent
    
    if total_budget > 0:
        budget_health = (total_spent / total_budget) * 100
        if budget_health > 100:
            budget_health = 100
    else:
        budget_health = 0
    
    # Get categories for form
    categories = Category.objects.filter(
        Q(user=request.user) | Q(is_system=True),
        category_type__in=['expense', 'both']
    )
    
    form = BudgetForm(user=request.user)
    
    if request.method == 'POST':
        form = BudgetForm(request.user, request.POST)
        if form.is_valid():
            b = form.save(commit=False)
            b.user = request.user
            b.month = month_start
            b.save()
            messages.success(request, 'Budget set successfully!')
            return redirect('budgets')
    
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    return render(request, 'fin_manager/budgets.html', {
        'budgets': budget_list,
        'form': form,
        'categories': categories,
        'currency': profile.get_currency_symbol(),
        'profile': profile,
        'month': month_start,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'remaining_budget': remaining_budget,
        'budget_health': budget_health,
    })

@login_required
def goals(request):
    all_goals = SavingsGoal.objects.filter(user=request.user)
    
    # Handle POST for new goal
    if request.method == 'POST':
        form = SavingsGoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, f'Goal "{goal.name}" created successfully!')
            return redirect('goals')
    
    total_target = sum(float(g.target_amount) for g in all_goals)
    total_saved = sum(float(g.current_amount) for g in all_goals)
    
    if total_target > 0:
        overall_progress = (total_saved / total_target) * 100
    else:
        overall_progress = 0
    
    active_goals = [g for g in all_goals if not g.is_completed]
    completed_goals = [g for g in all_goals if g.is_completed]
    
    today = date.today()
    upcoming_deadlines = sum(1 for g in active_goals 
                            if g.deadline and g.deadline <= today + timedelta(days=30))
    
    active_tab = request.GET.get('tab', 'active')
    
    form = SavingsGoalForm()
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    return render(request, 'fin_manager/goals.html', {
        'all_goals': all_goals,
        'active_goals': active_goals,
        'completed_goals': completed_goals,
        'active_goals_count': len(active_goals),
        'completed_goals_count': len(completed_goals),
        'total_target': total_target,
        'total_saved': total_saved,
        'overall_progress': overall_progress,
        'upcoming_deadlines': upcoming_deadlines,
        'active_tab': active_tab,
        'form': form,
        'currency': profile.get_currency_symbol(),
        'profile': profile,
    })


@login_required
def edit_goal(request, pk):
    goal = get_object_or_404(SavingsGoal, id=pk, user=request.user)
    tab = request.GET.get('tab', 'active')
    
    if request.method == 'POST':
        goal.name = request.POST.get('name')
        goal.target_amount = Decimal(request.POST.get('target_amount'))
        goal.current_amount = Decimal(request.POST.get('current_amount', 0))
        goal.priority = request.POST.get('priority', 'Medium')
        deadline = request.POST.get('deadline')
        goal.deadline = deadline if deadline else None
        goal.color = request.POST.get('color', '#1D9E75')
        
        if goal.current_amount >= goal.target_amount:
            goal.is_completed = True
            goal.completed_date = date.today()
        else:
            goal.is_completed = False
            goal.completed_date = None
        
        goal.save()
        messages.success(request, f'Goal "{goal.name}" updated.')
        return redirect(f'{reverse("goals")}?tab={tab}')
    
    return redirect(f'{reverse("goals")}?tab={tab}')


@login_required
def delete_goal(request, pk):
    goal = get_object_or_404(SavingsGoal, id=pk, user=request.user)
    goal_name = goal.name
    tab = request.GET.get('tab', 'active')
    goal.delete()
    messages.success(request, f'Goal "{goal_name}" deleted.')
    return redirect(f'{reverse("goals")}?tab={tab}')


@login_required
@require_POST
def goal_add_funds(request, pk):
    goal = get_object_or_404(SavingsGoal, id=pk, user=request.user)
    amount = Decimal(request.POST.get('amount', '0'))
    tab = request.POST.get('tab', 'active')
    
    if amount > 0:
        goal.current_amount += amount
        
        if goal.current_amount >= goal.target_amount:
            goal.is_completed = True
            goal.completed_date = date.today()
            messages.success(request, f'🎉 Congratulations! Goal "{goal.name}" completed!')
        else:
            profile = request.user.profile
            currency_symbol = profile.get_currency_symbol()
            messages.success(request, f'✅ Added {currency_symbol}{amount:,.2f} to "{goal.name}".')
        
        goal.save()
    else:
        messages.error(request, 'Please enter a valid amount greater than 0.')
    
    return redirect(f'{reverse("goals")}?tab={tab}')


@login_required
def get_goal_json(request, pk):
    goal = get_object_or_404(SavingsGoal, id=pk, user=request.user)
    return JsonResponse({
        'id': str(goal.id),
        'name': goal.name,
        'target_amount': float(goal.target_amount),
        'current_amount': float(goal.current_amount),
        'priority': goal.priority,
        'deadline': goal.deadline.isoformat() if goal.deadline else None,
        'color': goal.color,
    })


# Add these functions to your views.py (after your existing code)

@login_required
def liabilities(request):
    liability_list = Liability.objects.filter(user=request.user)
    form = LiabilityForm()

    if request.method == 'POST':
        # Check if this is an edit (has liability_id in POST)
        if request.POST.get('liability_id'):
            # This is handled by edit_liability view
            pass
        else:
            form = LiabilityForm(request.POST)
            if form.is_valid():
                l = form.save(commit=False)
                l.user = request.user
                l.save()
                messages.success(request, 'Liability added successfully!')
                return redirect('liabilities')

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    total_monthly = sum(
        float(l.monthly_payment) for l in liability_list if l.is_active
    )
    return render(request, 'fin_manager/liabilities.html', {
        'liabilities': liability_list,
        'form': form,
        'currency': profile.get_currency_symbol(),
        'profile': profile,
        'total_monthly': total_monthly,
    })


@login_required
def edit_liability(request, pk):
    liability = get_object_or_404(Liability, id=pk, user=request.user)
    
    if request.method == 'POST':
        liability.name = request.POST.get('name')
        liability.liability_type = request.POST.get('liability_type')
        liability.principal = Decimal(request.POST.get('principal'))
        liability.interest_rate = Decimal(request.POST.get('interest_rate', 0))
        liability.start_date = request.POST.get('start_date')
        liability.end_date = request.POST.get('end_date') or None
        liability.is_long_term = request.POST.get('is_long_term') == 'on'
        liability.is_active = request.POST.get('is_active') == 'on'
        liability.save()
        
        messages.success(request, f'Liability "{liability.name}" updated successfully!')
        return redirect('liabilities')
    
    return redirect('liabilities')


@login_required
def delete_liability(request, pk):
    liability = get_object_or_404(Liability, id=pk, user=request.user)
    liability_name = liability.name
    liability.delete()
    messages.success(request, f'Liability "{liability_name}" deleted successfully!')
    return redirect('liabilities')


@login_required
def get_liability_json(request, pk):
    liability = get_object_or_404(Liability, id=pk, user=request.user)
    return JsonResponse({
        'id': str(liability.id),
        'name': liability.name,
        'liability_type': liability.liability_type,
        'principal': float(liability.principal),
        'interest_rate': float(liability.interest_rate) if liability.interest_rate else None,
        'start_date': liability.start_date.isoformat(),
        'end_date': liability.end_date.isoformat() if liability.end_date else None,
        'is_long_term': liability.is_long_term,
        'is_active': liability.is_active,
        'monthly_payment': float(liability.monthly_payment),
    })


@login_required
def reports(request):
    service = DashboardService(request.user)
    prediction_service = BudgetPredictionService(request.user)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    trend = service.get_monthly_trend(12)
    score = service.get_financial_health_score()
    predictions = prediction_service.get_predictions()

    return render(request, 'fin_manager/reports.html', {
        'trend_json': json.dumps(trend),
        'score': score,
        'score_label': service._score_label(score),
        'score_color': service._score_color(score),
        'predictions': predictions,
        'currency': profile.get_currency_symbol(),
        'profile': profile,
    })


@login_required
def ai_insights(request):
    from django.db.models import Sum, Q
    from datetime import date
    from decimal import Decimal
    from django.conf import settings
    
    # Get current month
    today = date.today()
    current_month_start = today.replace(day=1)
    
    # Calculate monthly income
    monthly_income = Transaction.objects.filter(
        user=request.user,
        transaction_type='income',
        date__year=current_month_start.year,
        date__month=current_month_start.month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Calculate monthly expense
    monthly_expense = Transaction.objects.filter(
        user=request.user,
        transaction_type='expense',
        date__year=current_month_start.year,
        date__month=current_month_start.month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    # Calculate financial health
    if monthly_income > 0:
        financial_health = float(((monthly_income - monthly_expense) / monthly_income) * 100)
    else:
        financial_health = 0
    
    # Get top spending category
    from .models import Category
    top_category_data = Category.objects.filter(
        Q(user=request.user) | Q(is_system=True),
        category_type='expense'
    ).annotate(
        total=Sum('transactions__amount', filter=Q(
            transactions__user=request.user,
            transactions__transaction_type='expense',
            transactions__date__year=current_month_start.year,
            transactions__date__month=current_month_start.month
        ))
    ).filter(total__gt=0).order_by('-total').first()
    
    top_category = top_category_data.name if top_category_data else "No expenses yet"
    top_category_amount = float(top_category_data.total) if top_category_data else 0
    
    # Get profile
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    currency_symbol = profile.get_currency_symbol()
    
    # Initialize Groq service
    from .services import GroqInsightService
    groq_service = GroqInsightService()
    
    # Check if Groq is available
    ai_enabled = groq_service.is_available()
    
    # Handle refresh action
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'refresh':
            # Get anomalies for Groq
            anomalies_data = []
            try:
                from .services import TransactionService
                anomalies = TransactionService.detect_anomalies(request.user)
                for a in anomalies:
                    anomalies_data.append({
                        'category': a.get('category', 'Unknown'),
                        'current_amount': float(a.get('amount', 0)),
                        'average_amount': float(a.get('avg', 0)),
                        'increase_percent': float(a.get('multiplier', 0) * 100),
                    })
            except Exception:
                anomalies_data = []
            
            # Forecast data
            if monthly_expense > 0:
                predicted_expense = float(monthly_expense * Decimal('1.02'))
                predicted_savings = float(monthly_income) - predicted_expense if monthly_income > 0 else 0
                confidence = 85
                trend = "stable"
            else:
                predicted_expense = 0
                predicted_savings = 0
                confidence = 50
                trend = "stable"
            
            forecast_data = {
                'predicted_expense': predicted_expense,
                'predicted_savings': predicted_savings,
                'confidence': confidence,
                'trend': trend,
            }
            
            # Stats for Groq
            stats_for_groq = {
                'total_income': float(monthly_income),
                'total_expense': float(monthly_expense),
                'savings': float(monthly_income - monthly_expense),
                'savings_rate': financial_health,
                'top_category': top_category,
                'top_category_amount': top_category_amount,
                'currency': currency_symbol,
            }
            
            # Generate AI insights using Groq
            ai_insights_text = groq_service.generate_financial_insights(
                stats_for_groq, 
                anomalies_data, 
                forecast_data
            )
            
            if ai_insights_text:
                # Store in database
                AIInsight.objects.create(
                    user=request.user,
                    insight_type='ai_analysis',
                    title='Groq AI Financial Analysis',
                    body=ai_insights_text,
                    generated_at=timezone.now()
                )
                messages.success(request, 'AI insights generated successfully!')
            else:
                messages.warning(request, 'Could not generate AI insights. Please check your Groq API key.')
            
            return redirect('ai_insights')
    
    # Get rule-based insights for Insights tab
    rule_based_insights = []
    rule_based_recommendations = []
    
    if monthly_income > 0:
        savings_rate = float((monthly_income - monthly_expense) / monthly_income * 100)
        if savings_rate > 30:
            rule_based_insights.append(f"Excellent savings rate! You're saving {savings_rate:.1f}% of your income.")
        elif savings_rate > 15:
            rule_based_insights.append(f"Good savings rate of {savings_rate:.1f}%. Keep it up!")
        elif savings_rate > 0:
            rule_based_insights.append(f"Your savings rate is {savings_rate:.1f}%. Try to increase it to 20%.")
        else:
            rule_based_insights.append("You're spending more than you earn. Review your expenses.")
        
        rule_based_recommendations.append("Consider creating a budget to track your spending categories.")
    
    if top_category and top_category != "No expenses yet":
        rule_based_insights.append(f"Your largest expense category is {top_category} ({currency_symbol}{top_category_amount:,.2f}).")
        rule_based_recommendations.append(f"Review your {top_category} spending to see if you can reduce it by 10%.")
    
    # Get the latest AI insight from database
    latest_ai = AIInsight.objects.filter(
        user=request.user,
        insight_type='ai_analysis'
    ).order_by('-generated_at').first()
    
    ai_insights_text = latest_ai.body if latest_ai else None
    
    # Prepare insights data for template
    insights_data = {
        'insights': rule_based_insights,
        'recommendations': rule_based_recommendations,
    }
    
    # Get anomalies
    anomalies_data = []
    try:
        from .services import TransactionService
        anomalies = TransactionService.detect_anomalies(request.user)
        for a in anomalies:
            anomalies_data.append({
                'category': a.get('category', 'Unknown'),
                'current_amount': float(a.get('amount', 0)),
                'average_amount': float(a.get('avg', 0)),
                'increase_percent': float(a.get('multiplier', 0) * 100),
                'message': a.get('message', f"Spending is unusually high in this category."),
            })
    except Exception:
        anomalies_data = []
    
    # Forecast data
    if monthly_expense > 0:
        predicted_expense = float(monthly_expense * Decimal('1.02'))
        predicted_savings = float(monthly_income) - predicted_expense if monthly_income > 0 else 0
        confidence = 85
        trend = "stable"
    else:
        predicted_expense = 0
        predicted_savings = 0
        confidence = 50
        trend = "stable"
    
    forecast_data = {
        'predicted_expense': predicted_expense,
        'predicted_savings': predicted_savings,
        'confidence': confidence,
        'trend': trend,
    }
    
    # Get active tab
    active_tab = request.GET.get('tab', 'insights')
    
    context = {
        'insights': insights_data,
        'forecast': forecast_data,
        'anomalies': anomalies_data,
        'insights_count': len(rule_based_insights),
        'anomalies_count': len(anomalies_data),
        'forecast_available': True,
        'financial_health': financial_health,
        'monthly_income': float(monthly_income),
        'monthly_expense': float(monthly_expense),
        'top_category': top_category,
        'active_tab': active_tab,
        'ai_enabled': ai_enabled,
        'ai_insights': ai_insights_text,
        'currency': currency_symbol,
        'profile': profile,
    }
    
    return render(request, 'fin_manager/ai_insights.html', context)

@login_required
def settings_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    accounts = Account.objects.filter(user=request.user)
    account_form = AccountForm()

    if request.method == 'POST':
        # Check if this is profile edit from modal
        if 'first_name' in request.POST or 'email' in request.POST:
            # Update user info
            user = request.user
            if request.POST.get('first_name') is not None:
                user.first_name = request.POST.get('first_name', '')
            if request.POST.get('last_name') is not None:
                user.last_name = request.POST.get('last_name', '')
            if request.POST.get('email') is not None:
                user.email = request.POST.get('email', '')
            user.save()
            
            # Update profile
            if request.POST.get('currency'):
                profile.currency = request.POST.get('currency')
            if request.POST.get('timezone'):
                profile.timezone = request.POST.get('timezone')
            profile.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('settings')
        
        # Regular profile form (original)
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('settings')
    else:
        form = UserProfileForm(instance=profile)

    return render(request, 'fin_manager/settings.html', {
        'form': form,
        'account_form': account_form,
        'accounts': accounts,
        'profile': profile,
        'currency': profile.get_currency_symbol(),
    })


@login_required
def change_password(request):
    if request.method == 'POST':
        from django.contrib.auth import update_session_auth_hash
        from django.contrib.auth.forms import PasswordChangeForm
        
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('settings')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    
    return redirect('settings')


@login_required
def edit_account(request, pk):
    account = get_object_or_404(Account, id=pk, user=request.user)
    
    if request.method == 'POST':
        account.name = request.POST.get('name')
        account.account_type = request.POST.get('account_type')
        account.initial_balance = Decimal(request.POST.get('initial_balance', 0))
        account.color = request.POST.get('color', '#1D9E75')
        account.is_active = request.POST.get('is_active') == 'on'
        account.save()
        
        messages.success(request, f'Account "{account.name}" updated successfully!')
        return redirect('settings')
    
    return redirect('settings')


@login_required
def delete_account(request, pk):
    account = get_object_or_404(Account, id=pk, user=request.user)
    account_name = account.name
    account.delete()
    messages.success(request, f'Account "{account_name}" deleted successfully!')
    return redirect('settings')


@login_required
def get_account_json(request, pk):
    account = get_object_or_404(Account, id=pk, user=request.user)
    return JsonResponse({
        'id': str(account.id),
        'name': account.name,
        'account_type': account.account_type,
        'initial_balance': float(account.initial_balance),
        'color': account.color,
        'is_active': account.is_active,
        'balance': float(account.balance),
    })


@login_required
@require_POST
def add_account(request):
    form = AccountForm(request.POST)
    if form.is_valid():
        a = form.save(commit=False)
        a.user = request.user
        a.save()
        messages.success(request, 'Account added.')
    return redirect('settings')


@login_required
@require_POST
def delete_transaction(request, pk):
    t = get_object_or_404(Transaction, id=pk, user=request.user)
    t.delete()
    messages.success(request, 'Transaction deleted.')
    return redirect('transactions')