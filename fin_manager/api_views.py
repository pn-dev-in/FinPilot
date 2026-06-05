from rest_framework import viewsets, generics, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.models import User
from django.db.models import Sum, Q
from datetime import date
from decimal import Decimal

from .models import (
    Account, Category, Transaction, Budget,
    Liability, SavingsGoal, AIInsight, RecurringRule
)
from .serializers import (
    AccountSerializer, CategorySerializer, TransactionSerializer,
    BudgetSerializer, LiabilitySerializer, SavingsGoalSerializer,
    AIInsightSerializer, RecurringRuleSerializer,
    UserRegistrationSerializer, NaturalLanguageInputSerializer
)
from .services import DashboardService, InsightService, BudgetPredictionService, TransactionService
from .filters import TransactionFilter


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer


class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user, is_active=True)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(
            Q(user=self.request.user) | Q(is_system=True)
        )


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    filterset_class = TransactionFilter
    search_fields = ['description', 'notes']
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date']

    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user
        ).select_related('category', 'account')

    @action(detail=False, methods=['get'])
    def by_month(self, request):
        year = request.query_params.get('year', date.today().year)
        month = request.query_params.get('month', date.today().month)
        qs = self.get_queryset().filter(date__year=year, date__month=month)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        qs = self.get_queryset()
        year = request.query_params.get('year', date.today().year)
        month = request.query_params.get('month', date.today().month)
        qs = qs.filter(date__year=year, date__month=month)
        income = qs.filter(transaction_type='income').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        expense = qs.filter(transaction_type='expense').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        return Response({
            'income': income,
            'expense': expense,
            'savings': income - expense,
        })


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user).select_related('category')

    @action(detail=False, methods=['get'])
    def current_month(self, request):
        today = date.today()
        qs = self.get_queryset().filter(
            month__year=today.year,
            month__month=today.month,
        )
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class LiabilityViewSet(viewsets.ModelViewSet):
    serializer_class = LiabilitySerializer

    def get_queryset(self):
        return Liability.objects.filter(user=self.request.user)


class SavingsGoalViewSet(viewsets.ModelViewSet):
    serializer_class = SavingsGoalSerializer

    def get_queryset(self):
        return SavingsGoal.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def add_funds(self, request, pk=None):
        goal = self.get_object()
        amount = Decimal(str(request.data.get('amount', 0)))
        if amount <= 0:
            return Response({'error': 'Amount must be positive.'}, status=400)
        goal.current_amount += amount
        if goal.current_amount >= goal.target_amount:
            goal.is_completed = True
        goal.save()
        return Response(self.get_serializer(goal).data)


class RecurringRuleViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringRuleSerializer

    def get_queryset(self):
        return RecurringRule.objects.filter(user=self.request.user)


class DashboardView(APIView):
    def get(self, request):
        service = DashboardService(request.user)
        context = service.get_full_context()
        # Serialise non-serialisable objects
        context['recent_transactions'] = TransactionSerializer(
            context['recent_transactions'], many=True
        ).data
        context['ai_insights'] = AIInsightSerializer(
            context['ai_insights'], many=True
        ).data
        # Convert Decimal to float for JSON
        for key in ['balance', 'income', 'expense', 'savings']:
            context[key] = float(context[key])
        context['expense_by_category'] = [
            {
                'category': c['category__name'],
                'color': c['category__color'],
                'icon': c['category__icon'],
                'total': float(c['total']),
            }
            for c in context['expense_by_category']
        ]
        return Response(context)


class AIInsightsView(APIView):
    def get(self, request):
        service = InsightService(request.user)
        insights = service.generate_insights()
        return Response(AIInsightSerializer(insights, many=True).data)

    def post(self, request):
        """Mark all insights as read."""
        AIInsight.objects.filter(user=request.user).update(is_read=True)
        return Response({'status': 'ok'})


class NLPTransactionView(APIView):
    def post(self, request):
        serializer = NaturalLanguageInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        text = serializer.validated_data['text']
        account_id = serializer.validated_data['account_id']

        try:
            account = Account.objects.get(id=account_id, user=request.user)
        except Account.DoesNotExist:
            return Response({'error': 'Account not found.'}, status=404)

        data, error = TransactionService.create_from_natural_language(request.user, text)
        if error:
            return Response({'error': error}, status=400)

        # Try to match category hint
        category = None
        hint = data.get('category_hint', 'other')
        cat_qs = Category.objects.filter(
            Q(user=request.user) | Q(is_system=True),
            icon=hint
        )
        if cat_qs.exists():
            category = cat_qs.first()

        transaction = Transaction.objects.create(
            user=request.user,
            account=account,
            category=category,
            transaction_type=data.get('transaction_type', 'expense'),
            amount=Decimal(str(data.get('amount', 0))),
            description=data.get('description', text),
            date=data.get('date', date.today()),
            ai_categorised=True,
        )
        return Response(TransactionSerializer(transaction).data, status=201)


class PredictionsView(APIView):
    def get(self, request):
        service = BudgetPredictionService(request.user)
        return Response(service.get_predictions())


class ReportSummaryView(APIView):
    def get(self, request):
        service = DashboardService(request.user)
        months = int(request.query_params.get('months', 6))
        return Response({
            'trend': service.get_monthly_trend(months),
            'health_score': service.get_financial_health_score(),
            'expense_by_category': [
                {
                    'category': c['category__name'],
                    'total': float(c['total']),
                    'color': c['category__color'],
                }
                for c in service.get_expense_by_category()
            ],
        })
