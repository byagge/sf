from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import OrderStage
from .serializers import OrderStageSerializer
from django.shortcuts import get_object_or_404

class WorkshopStagesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        workshop_id = request.GET.get('workshop')
        status = request.GET.get('status')
        stages = OrderStage.objects.select_related(
            'order',
            'order__client',
            'order_item__product',
            'order_item__order',
            'order_item__order__client',
            'workshop'
        ).prefetch_related(
            'order__items__product',
            'order_item__order__items__product'
        ).filter(workshop_id=workshop_id, status=status)
        return Response(OrderStageSerializer(stages, many=True).data) 

class StageDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, stage_id):
        stage = get_object_or_404(
            OrderStage.objects.select_related(
                'order',
                'order__client',
                'order_item__product',
                'order_item__order',
                'order_item__order__client',
                'workshop'
            ).prefetch_related(
                'order__items__product',
                'order_item__order__items__product'
            ),
            id=stage_id
        )
        return Response(OrderStageSerializer(stage).data) 