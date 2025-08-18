# Generated manually for new defect system

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employee_tasks', '0005_employeetask_earnings_employeetask_net_earnings_and_more'),
        ('defects', '0002_rename_can_be_fixed_defect_is_repairable_and_more'),
    ]

    operations = [
        # Step 1: Add the field as nullable first
        migrations.AddField(
            model_name='defect',
            name='employee_task',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='defects',
                to='employee_tasks.employeetask',
                verbose_name='Задача сотрудника',
                null=True,  # Make it nullable initially
                blank=True,
            ),
        ),
        # Step 2: Populate the field with a default value for existing records
        # This will be handled by a data migration or by the application logic
        # Step 3: Make the field required (this will be done in a future migration)
    ] 