"""
Service layer — all business logic lives here, views stay thin.
"""
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.conf import settings


from .models import (
    Transaction, Budget, AIInsight, Account,
    Category, SavingsGoal, Liability, RecurringRule
)


# services.py - Replace the GroqInsightService class with this

class GroqInsightService:
    """Fallback service that generates insights without any API key"""
    
    def __init__(self, api_key=None):
        self.api_key = None  # No API key needed
        self.client = None
        self.model = 'fallback'
    
    def is_available(self):
        """Always available - no API key needed"""
        return True
    
    def generate_financial_insights(self, stats_data, anomalies, forecast):
        """Generate insights using rule-based logic (no API needed)"""
        
        currency = stats_data.get('currency', '₹')
        income = stats_data.get('total_income', 0)
        expense = stats_data.get('total_expense', 0)
        savings = stats_data.get('savings', 0)
        savings_rate = stats_data.get('savings_rate', 0)
        top_category = stats_data.get('top_category', 'Unknown')
        top_amount = stats_data.get('top_category_amount', 0)
        
        insights_text = f"""
💡 FINANCIAL ANALYSIS REPORT

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 INCOME & EXPENSE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Monthly Income: {currency}{income:,.2f}
• Monthly Expenses: {currency}{expense:,.2f}
• Net Savings: {currency}{savings:,.2f}
• Savings Rate: {savings_rate:.1f}%

"""

        # Add savings insights
        if savings_rate >= 30:
            insights_text += f"""
✅ SAVINGS RATE: EXCELLENT!
   You're saving {savings_rate:.1f}% of your income.
   This is well above the recommended 20% target.

"""
        elif savings_rate >= 20:
            insights_text += f"""
✅ SAVINGS RATE: GOOD
   You're saving {savings_rate:.1f}% of your income.
   You've met the recommended 20% savings target!

"""
        elif savings_rate >= 10:
            insights_text += f"""
📈 SAVINGS RATE: FAIR
   Your savings rate is {savings_rate:.1f}%.
   Try to increase this to 20% for better financial security.

"""
        else:
            insights_text += f"""
⚠️ SAVINGS RATE: NEEDS IMPROVEMENT
   You're only saving {savings_rate:.1f}% of your income.
   Aim to save at least 20% of your monthly income.

"""

        # Add category insights
        if top_category and top_category != "No expenses yet":
            insights_text += f"""
🏆 TOP SPENDING CATEGORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Category: {top_category}
• Amount: {currency}{top_amount:,.2f}
• This is your largest expense area this month.

"""

        # Add anomaly insights
        if anomalies and len(anomalies) > 0:
            insights_text += f"""
⚠️ SPENDING ANOMALIES DETECTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
We detected unusual spending in the following categories:
"""
            for anomaly in anomalies[:3]:
                insights_text += f"• {anomaly.get('category', 'Unknown')}: {anomaly.get('increase_percent', 0):.0f}% higher than usual\n"
            insights_text += "\n"
        else:
            insights_text += """
✅ NO ANOMALIES DETECTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Your spending patterns are consistent with previous months.

"""

        # Add forecast
        if forecast.get('predicted_expense', 0) > 0:
            insights_text += f"""
🔮 NEXT MONTH FORECAST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Predicted Expenses: {currency}{forecast.get('predicted_expense', 0):,.2f}
• Predicted Savings: {currency}{forecast.get('predicted_savings', 0):,.2f}
• Confidence Level: {forecast.get('confidence', 85)}%

"""

        # Add recommendations
        insights_text += """
💡 ACTIONABLE RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        if savings_rate < 20:
            insights_text += "• 📉 Reduce discretionary spending by 10% next month\n"
        if top_category and top_category != "No expenses yet":
            insights_text += f"• 🎯 Review your {top_category} expenses and look for savings opportunities\n"
        
        insights_text += "• 📋 Create category budgets to track your spending better\n"
        insights_text += "• 💰 Automate your savings by setting up recurring transfers\n"
        insights_text += "• 📊 Review your expenses weekly to stay on track\n"

        insights_text += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💪 Keep up the good work! Small changes add up over time.
"""
        
        return insights_text
    
    def test_connection(self):
        """Always returns success"""
        return True, "Fallback mode active - No API key needed"


class DashboardService:
    def __init__(self, user):
        self.user = user
        today = date.today()
        self.current_month_start = today.replace(day=1)
        self.last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

    def get_monthly_income(self, month_start=None):
        start = month_start or self.current_month_start
        end = (start + relativedelta(months=1)) - timedelta(days=1)
        result = Transaction.objects.filter(
            user=self.user,
            transaction_type='income',
            date__gte=start,
            date__lte=end,
        ).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0')

    def get_monthly_expense(self, month_start=None):
        start = month_start or self.current_month_start
        end = (start + relativedelta(months=1)) - timedelta(days=1)
        result = Transaction.objects.filter(
            user=self.user,
            transaction_type='expense',
            date__gte=start,
            date__lte=end,
        ).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0')

    def get_total_balance(self):
        accounts = Account.objects.filter(user=self.user, is_active=True)
        return sum(a.balance for a in accounts)

    def get_net_savings(self):
        return self.get_monthly_income() - self.get_monthly_expense()

    def get_financial_health_score(self):
        """
        Score 0-100 based on:
        - Savings ratio (40 pts): savings/income
        - Expense control (40 pts): expense vs income ratio
        - EMI burden (20 pts): total EMI vs income
        """
        income = float(self.get_monthly_income())
        expense = float(self.get_monthly_expense())
        if income == 0:
            return 50  # neutral if no data

        # Savings ratio score (0-40)
        savings_ratio = max(0, (income - expense) / income)
        savings_score = min(40, savings_ratio * 100 * 0.4)

        # Expense control score (0-40)
        expense_ratio = expense / income
        if expense_ratio <= 0.5:
            expense_score = 40
        elif expense_ratio <= 0.7:
            expense_score = 30
        elif expense_ratio <= 0.9:
            expense_score = 20
        elif expense_ratio <= 1.0:
            expense_score = 10
        else:
            expense_score = 0

        # EMI burden score (0-20)
        total_emi = float(sum(
            l.monthly_payment for l in
            Liability.objects.filter(user=self.user, is_active=True, is_long_term=True)
        ))
        emi_ratio = total_emi / income if income > 0 else 0
        if emi_ratio <= 0.2:
            emi_score = 20
        elif emi_ratio <= 0.35:
            emi_score = 15
        elif emi_ratio <= 0.5:
            emi_score = 8
        else:
            emi_score = 0

        total = round(savings_score + expense_score + emi_score)
        return max(0, min(100, total))

    def get_expense_by_category(self, month_start=None):
        start = month_start or self.current_month_start
        end = (start + relativedelta(months=1)) - timedelta(days=1)
        return Transaction.objects.filter(
            user=self.user,
            transaction_type='expense',
            date__gte=start,
            date__lte=end,
            category__isnull=False,
        ).values(
            'category__name', 'category__color', 'category__icon'
        ).annotate(total=Sum('amount')).order_by('-total')

    def get_monthly_trend(self, months=6):
        """Returns income and expense totals for the last N months."""
        result = []
        today = date.today()
        for i in range(months - 1, -1, -1):
            month_start = (today.replace(day=1) - relativedelta(months=i))
            income = float(self.get_monthly_income(month_start))
            expense = float(self.get_monthly_expense(month_start))
            result.append({
                'month': month_start.strftime('%b %Y'),
                'income': income,
                'expense': expense,
                'savings': income - expense,
            })
        return result

    def get_budget_utilisation(self):
        today = date.today()
        month_start = today.replace(day=1)
        budgets = Budget.objects.filter(
            user=self.user,
            month=month_start,
        ).select_related('category')
        return [
            {
                'id': str(b.id),
                'category': b.category.name,
                'color': b.category.color,
                'icon': b.category.icon,
                'limit': float(b.limit_amount),
                'spent': float(b.spent),
                'percent': b.percent_used,
                'remaining': float(b.remaining),
                'is_over': b.is_over_budget,
                'is_near': b.is_near_limit,
            }
            for b in budgets
        ]

    def get_recent_transactions(self, limit=10):
        return Transaction.objects.filter(
            user=self.user
        ).select_related('category', 'account')[:limit]

    def get_upcoming_recurring(self, days=7):
        cutoff = date.today() + timedelta(days=days)
        return RecurringRule.objects.filter(
            user=self.user,
            is_active=True,
            next_due__lte=cutoff,
        ).select_related('category', 'account').order_by('next_due')

    def get_delta_percent(self, current, previous):
        if previous == 0:
            return None
        return round(float((current - previous) / previous * 100), 1)

    def get_full_context(self):
        income = self.get_monthly_income()
        last_income = self.get_monthly_income(self.last_month_start)
        expense = self.get_monthly_expense()
        last_expense = self.get_monthly_expense(self.last_month_start)
        savings = income - expense
        last_savings = last_income - last_expense
        balance = self.get_total_balance()
        score = self.get_financial_health_score()

        return {
            'balance': balance,
            'income': income,
            'expense': expense,
            'savings': savings,
            'income_delta': self.get_delta_percent(income, last_income),
            'expense_delta': self.get_delta_percent(expense, last_expense),
            'savings_delta': self.get_delta_percent(savings, last_savings),
            'health_score': score,
            'score_label': self._score_label(score),
            'score_color': self._score_color(score),
            'expense_by_category': list(self.get_expense_by_category()),
            'monthly_trend': self.get_monthly_trend(),
            'budget_utilisation': self.get_budget_utilisation(),
            'recent_transactions': self.get_recent_transactions(),
            'upcoming_recurring': self.get_upcoming_recurring(),
            'ai_insights': AIInsight.objects.filter(user=self.user, is_read=False)[:3],
        }

    def _score_label(self, score):
        if score >= 80:
            return 'Excellent'
        elif score >= 60:
            return 'Good'
        elif score >= 40:
            return 'Fair'
        else:
            return 'Needs Attention'

    def _score_color(self, score):
        if score >= 80:
            return '#1D9E75'
        elif score >= 60:
            return '#378ADD'
        elif score >= 40:
            return '#BA7517'
        else:
            return '#D85A30'


class TransactionService:
    @staticmethod
    def create_from_natural_language(user, text):
        """
        Parse natural language like "Spent ₹450 on Zomato yesterday"
        using Groq API and create a transaction.
        """
        from django.conf import settings
        if not settings.GROQ_API_KEY:
            return None, "GROQ API key not configured."

        try:
            from groq import Groq

            client = Groq(api_key=settings.GROQ_API_KEY)
            today = date.today().isoformat()
            
            prompt = f"""
Parse this expense description and return JSON.

Description: "{text}"
Today's date: {today}

Return ONLY valid JSON (no other text):
{{
    "amount": 450.00,
    "category": "Food",
    "date": "2026-06-04",
    "note": "Zomato order",
    "transaction_type": "expense"
}}
"""
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
            )
            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)
            return data, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def detect_anomalies(user):
        """Flag transactions that are 2+ std deviations above category average."""
        from django.db.models import StdDev
        import math

        alerts = []
        today = date.today()
        three_months_ago = today - relativedelta(months=3)

        categories = Category.objects.filter(
            transactions__user=user
        ).distinct()

        for cat in categories:
            stats = Transaction.objects.filter(
                user=user,
                category=cat,
                transaction_type='expense',
                date__gte=three_months_ago,
                date__lt=today.replace(day=1),
            ).aggregate(avg=Avg('amount'), std=StdDev('amount'))

            avg = float(stats['avg'] or 0)
            std = float(stats['std'] or 0)
            if avg == 0 or std == 0:
                continue

            threshold = avg + 2 * std
            recent = Transaction.objects.filter(
                user=user,
                category=cat,
                transaction_type='expense',
                date__gte=today.replace(day=1),
                amount__gt=threshold,
            )
            for t in recent:
                alerts.append({
                    'transaction': t,
                    'category': cat.name,
                    'amount': float(t.amount),
                    'avg': round(avg, 2),
                    'multiplier': round(float(t.amount) / avg, 1),
                })
        return alerts


class InsightService:
    def __init__(self, user):
        self.user = user

    def generate_insights(self):
        """Generate AI insights using Groq API. Call max once per week."""
        from django.conf import settings
        from datetime import timedelta

        # Check if recent insights exist (within 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        if AIInsight.objects.filter(user=self.user, generated_at__gte=week_ago).exists():
            return AIInsight.objects.filter(user=self.user)[:5]

        if not settings.GROQ_API_KEY:
            # Always use rule-based insights (no API key needed)
            return self._get_rule_based_insights()

        # Build transaction summary for Groq
        service = DashboardService(self.user)
        trend = service.get_monthly_trend(3)
        categories = list(service.get_expense_by_category())
        income = float(service.get_monthly_income())
        expense = float(service.get_monthly_expense())
        savings = income - expense
        savings_rate = round(savings / income * 100, 1) if income > 0 else 0

        summary = {
            'monthly_trend': trend,
            'top_categories': [
                {'category': c['category__name'], 'amount': float(c['total'])}
                for c in categories[:5]
            ],
            'current_month': {
                'income': income,
                'expense': expense,
                'savings': savings,
                'savings_rate': savings_rate,
            }
        }

        try:
            from groq import Groq
            from django.conf import settings
            prompt = f"""
You are a financial advisor.

Analyze this user's finances.

Income: {income}

Expense: {expense}

Savings: {savings}

Savings Rate: {savings_rate}%

Top Categories:
{json.dumps(summary['top_categories'], indent=2)}

Monthly Trend:
{json.dumps(trend, indent=2)}

Provide:

1. 5 financial insights
2. 5 recommendations
3. Risk warnings if any

Return JSON:

[
  {{
    "type":"trend",
    "title":"Insight title",
    "body":"Insight text",
    "change_percent":0
  }}
]
"""

            client = Groq(api_key=settings.GROQ_API_KEY)
            today = date.today().isoformat()
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1200,
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "")
            raw = raw.replace("```", "")

            insights_data = json.loads(raw)

            # Delete old insights, save new ones
            AIInsight.objects.filter(user=self.user).delete()
            created = []
            for item in insights_data:
                insight = AIInsight.objects.create(
                    user=self.user,
                    insight_type=item.get('type', 'trend'),
                    title=item.get('title', 'Financial Insight'),
                    body=item.get('body', ''),
                    change_percent=item.get('change_percent'),
                )
                created.append(insight)
            return created
        except Exception:
            return self._get_rule_based_insights()

    def _get_rule_based_insights(self):
        """Fallback insights without AI."""
        service = DashboardService(self.user)
        income = float(service.get_monthly_income())
        expense = float(service.get_monthly_expense())
        insights = []

        if income > 0:
            savings_rate = (income - expense) / income * 100
            if savings_rate < 20:
                AIInsight.objects.filter(user=self.user).delete()
                i = AIInsight.objects.create(
                    user=self.user,
                    insight_type='saving',
                    title='Your savings rate is below 20%',
                    body=f'You saved {savings_rate:.1f}% this month. Financial experts recommend saving at least 20% of income.',
                    change_percent=savings_rate,
                )
                insights.append(i)
        return insights


class BudgetPredictionService:
    def __init__(self, user):
        self.user = user

    def get_predictions(self):
        """Predict end-of-month spend per category using 3-month rolling average."""
        today = date.today()
        days_elapsed = today.day
        days_in_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        days_remaining = days_in_month.day - days_elapsed

        predictions = []
        categories = Category.objects.filter(
            transactions__user=self.user,
            transactions__transaction_type='expense'
        ).distinct()

        for cat in categories:
            # 3-month average
            monthly_avgs = []
            for i in range(1, 4):
                month_start = (today.replace(day=1) - relativedelta(months=i))
                month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
                total = Transaction.objects.filter(
                    user=self.user,
                    category=cat,
                    transaction_type='expense',
                    date__gte=month_start,
                    date__lte=month_end,
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                monthly_avgs.append(float(total))

            if not any(monthly_avgs):
                continue

            avg_monthly = sum(monthly_avgs) / len([x for x in monthly_avgs if x > 0])

            # Current month so far
            current = float(
                Transaction.objects.filter(
                    user=self.user,
                    category=cat,
                    transaction_type='expense',
                    date__gte=today.replace(day=1),
                    date__lte=today,
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            )

            daily_rate = current / days_elapsed if days_elapsed > 0 else 0
            projected = current + daily_rate * days_remaining

            predictions.append({
                'category': cat.name,
                'color': cat.color,
                'icon': cat.icon,
                'current': round(current, 2),
                'projected': round(projected, 2),
                'avg_monthly': round(avg_monthly, 2),
                'over_average': projected > avg_monthly,
            })

        return sorted(predictions, key=lambda x: x['projected'], reverse=True)