from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid
import datetime


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('currency', models.CharField(choices=[('INR', '₹ Indian Rupee'), ('USD', '$ US Dollar'), ('EUR', '€ Euro'), ('GBP', '£ British Pound')], default='INR', max_length=3)),
                ('monthly_income', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('timezone', models.CharField(default='Asia/Kolkata', max_length=50)),
                ('avatar_initial', models.CharField(default='FP', max_length=2)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('account_type', models.CharField(choices=[('bank', 'Bank Account'), ('cash', 'Cash Wallet'), ('credit', 'Credit Card'), ('savings', 'Savings Account'), ('investment', 'Investment')], default='bank', max_length=20)),
                ('initial_balance', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('is_active', models.BooleanField(default=True)),
                ('color', models.CharField(default='#1D9E75', max_length=7)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accounts', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('icon', models.CharField(choices=[('food', 'Food & Dining'), ('transport', 'Transport'), ('housing', 'Housing & Rent'), ('health', 'Health'), ('entertainment', 'Entertainment'), ('shopping', 'Shopping'), ('education', 'Education'), ('subscriptions', 'Subscriptions'), ('utilities', 'Utilities'), ('salary', 'Salary'), ('freelance', 'Freelance'), ('investment', 'Investment'), ('transfer', 'Transfer'), ('other', 'Other')], default='other', max_length=30)),
                ('color', models.CharField(default='#1D9E75', max_length=7)),
                ('category_type', models.CharField(choices=[('income', 'Income'), ('expense', 'Expense'), ('both', 'Both')], default='expense', max_length=10)),
                ('is_system', models.BooleanField(default=False)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='categories', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['name'], 'verbose_name_plural': 'categories'},
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('transaction_type', models.CharField(choices=[('income', 'Income'), ('expense', 'Expense'), ('transfer', 'Transfer')], max_length=10)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('description', models.CharField(max_length=255)),
                ('date', models.DateField(db_index=True)),
                ('notes', models.TextField(blank=True)),
                ('is_recurring', models.BooleanField(default=False)),
                ('ai_categorised', models.BooleanField(default=False)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='fin_manager.account')),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='fin_manager.category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date', '-created_at']},
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'date'], name='fin_manager_user_id_date_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'transaction_type'], name='fin_manager_user_id_type_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['user', 'category'], name='fin_manager_user_id_cat_idx'),
        ),
        migrations.CreateModel(
            name='RecurringRule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('transaction_type', models.CharField(choices=[('income', 'Income'), ('expense', 'Expense'), ('transfer', 'Transfer')], max_length=10)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('description', models.CharField(max_length=255)),
                ('frequency', models.CharField(choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('yearly', 'Yearly')], default='monthly', max_length=10)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('next_due', models.DateField()),
                ('is_active', models.BooleanField(default=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='fin_manager.account')),
                ('category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='fin_manager.category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recurring_rules', to=settings.AUTH_USER_MODEL)),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='Budget',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('month', models.DateField()),
                ('limit_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('alert_threshold', models.IntegerField(default=80)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budgets', to='fin_manager.category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budgets', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-month'], 'unique_together': {('user', 'category', 'month')}},
        ),
        migrations.CreateModel(
            name='Liability',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('liability_type', models.CharField(choices=[('emi', 'EMI / Loan'), ('credit_card', 'Credit Card'), ('personal', 'Personal Loan'), ('one_time', 'One-time Payment')], default='emi', max_length=20)),
                ('principal', models.DecimalField(decimal_places=2, max_digits=12)),
                ('interest_rate', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=5, null=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_long_term', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='liabilities', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='SavingsGoal',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('target_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('current_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('deadline', models.DateField(blank=True, null=True)),
                ('icon', models.CharField(default='target', max_length=30)),
                ('color', models.CharField(default='#1D9E75', max_length=7)),
                ('is_completed', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='savings_goals', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='AIInsight',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('insight_type', models.CharField(choices=[('trend', 'Spending Trend'), ('anomaly', 'Anomaly Detected'), ('saving', 'Savings Opportunity'), ('budget', 'Budget Alert'), ('forecast', 'Forecast')], default='trend', max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('body', models.TextField()),
                ('change_percent', models.FloatField(blank=True, null=True)),
                ('is_read', models.BooleanField(default=False)),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ai_insights', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-generated_at']},
        ),
    ]
