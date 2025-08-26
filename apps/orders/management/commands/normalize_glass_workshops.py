from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.orders.models import OrderStage
from apps.operations.workshops.models import Workshop


class Command(BaseCommand):
    help = (
        "Move glass order stages that are in non-compliant workshops to workshop ID 2. "
        "Aggregates remaining quantity into an appropriate stage at workshop 2 and "
        "shrinks original stage plan to its completed amount."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Show what would be changed without saving to the database.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            default=False,
            help="Verbose output for each processed stage.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options.get("dry_run", False)
        verbose: bool = options.get("verbose", False)

        try:
            target_workshop = Workshop.objects.get(pk=2)
        except Workshop.DoesNotExist:
            self.stderr.write(self.style.ERROR("Workshop with ID 2 does not exist"))
            return

        # Find glass stages not in workshops 2 or 12
        offending_qs = (
            OrderStage.objects.select_related("order_item__product", "workshop", "order")
            .filter(order_item__product__is_glass=True)
            .exclude(workshop_id__in=(2, 12))
        )

        total = offending_qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No offending glass stages found. Nothing to do."))
            return

        self.stdout.write(f"Found {total} glass stages in non-compliant workshops. Target: workshop 2")

        moved_count = 0
        aggregated_qty_total = 0

        @transaction.atomic
        def process_stage(stage: OrderStage):
            nonlocal moved_count, aggregated_qty_total

            remaining_qty = max(0, int(stage.plan_quantity) - int(stage.completed_quantity or 0))
            if remaining_qty == 0:
                if verbose:
                    self.stdout.write(f"Stage #{stage.id}: nothing to move (remaining 0). Skipping.")
                return

            # Find or create the destination stage in workshop 2, preserving order_item and parallel_group
            dest_stage = (
                OrderStage.objects.filter(
                    order=stage.order,
                    order_item=stage.order_item,
                    workshop_id=2,
                    stage_type='workshop',
                    parallel_group=stage.parallel_group,
                )
                .order_by('sequence')
                .first()
            )

            if dest_stage:
                dest_stage.plan_quantity = int(dest_stage.plan_quantity) + remaining_qty
                dest_stage.status = 'in_progress'
                if not dry_run:
                    dest_stage.save(update_fields=["plan_quantity", "status"]) 
                action = f"aggregated +{remaining_qty} into existing stage #{dest_stage.id}"
            else:
                # Create a new destination stage right after current stage's sequence
                dest_stage = OrderStage(
                    order=stage.order,
                    order_item=stage.order_item,
                    sequence=(stage.sequence or 0) + 1,
                    stage_type='workshop',
                    workshop=target_workshop,
                    operation=f"Перенос (скрипт) из: {stage.workshop.name if stage.workshop else ''}",
                    plan_quantity=remaining_qty,
                    deadline=timezone.now().date(),
                    status='in_progress',
                    parallel_group=stage.parallel_group,
                )
                if not dry_run:
                    dest_stage.save()
                action = f"created new stage #{'(unsaved)' if dry_run else dest_stage.id} with +{remaining_qty}"

            # Shrink original stage plan to its completed amount and mark status accordingly
            new_plan = int(stage.completed_quantity or 0)
            new_status = 'done' if new_plan >= int(stage.plan_quantity) else 'in_progress'
            if verbose:
                self.stdout.write(
                    f"Stage #{stage.id} @WS {stage.workshop_id} -> WS 2: {action}; "
                    f"original plan={stage.plan_quantity}, completed={stage.completed_quantity}, remaining moved={remaining_qty}"
                )

            if not dry_run:
                stage.plan_quantity = new_plan
                stage.status = new_status
                # Annotate comment
                move_note = f" | Moved {remaining_qty} to WS2 by normalize_glass_workshops"
                stage.comment = (stage.comment or "") + move_note
                stage.save(update_fields=["plan_quantity", "status", "comment"]) 

            moved_count += 1
            aggregated_qty_total += remaining_qty

        # Iterate
        for stage in offending_qs.iterator():
            process_stage(stage)

        note = "(dry-run) " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{note}Processed {moved_count} stages; aggregated total quantity moved to WS2: {aggregated_qty_total}"
            )
        ) 