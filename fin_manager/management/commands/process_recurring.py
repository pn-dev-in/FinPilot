from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from fin_manager.models import RecurringRule, Transaction


class Command(BaseCommand):
    help = 'Process recurring transactions that are due today'

    def handle(self, *args, **options):
        today = date.today()
        due_rules = RecurringRule.objects.filter(
            is_active=True,
            next_due__lte=today,
        ).select_related('user', 'account', 'category')

        created_count = 0
        for rule in due_rules:
            # Check end date
            if rule.end_date and today > rule.end_date:
                rule.is_active = False
                rule.save()
                continue

            Transaction.objects.create(
                user=rule.user,
                account=rule.account,
                category=rule.category,
                transaction_type=rule.transaction_type,
                amount=rule.amount,
                description=rule.description,
                date=today,
                is_recurring=True,
            )
            rule.advance_next_due()
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Created {created_count} recurring transactions.')
        )
