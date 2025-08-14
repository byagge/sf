from django.shortcuts import render
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.clients.models import Client
from .serializers import ClientSerializer
from django.db import models

# Create your views here.

# API: Список и создание клиентов
class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all().order_by('-created_at')
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(phone__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(company__icontains=search)
            )
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=201)
        print('CLIENT CREATE ERROR:', serializer.errors, 'DATA:', request.data)
        return Response(serializer.errors, status=400)

def clients_page(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(m in user_agent for m in ['android', 'iphone', 'ipad', 'mobile'])
    template = 'clients_mobile.html' if is_mobile else 'clients.html'
    return render(request, template)
