from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import Service, ServiceMaterial, RawMaterial, Workshop
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from django.forms.models import model_to_dict
from django.db.models import Sum, Count, Avg
from apps.inventory.models import RawMaterial


def service_list(request):
    query = request.GET.get('q', '')
    services = Service.objects.all()
    if query:
        services = services.filter(
            Q(name__icontains=query) | Q(code__icontains=query) | Q(description__icontains=query)
        )
    
    # Определение мобильного устройства по User-Agent
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = any(mobile in user_agent for mobile in [
        'mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 
        'windows phone', 'opera mini', 'mobile safari'
    ])
    
    # Выбор шаблона в зависимости от устройства
    template = 'services_mobile.html' if is_mobile else 'services.html'
    
    return render(request, template, {
        'services': services,
        'query': query,
    })


def service_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description', '')
        unit = request.POST.get('unit', 'услуга')
        price = request.POST.get('price', 0)
        is_active = request.POST.get('is_active', 'on') == 'on'
        Service.objects.create(
            name=name, code=code, description=description, unit=unit, price=price, is_active=is_active
        )
        return redirect('service_list')
    return render(request, 'service_form.html')


def service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        service.name = request.POST.get('name')
        service.code = request.POST.get('code')
        service.description = request.POST.get('description', '')
        service.unit = request.POST.get('unit', 'услуга')
        service.price = request.POST.get('price', 0)
        service.is_active = request.POST.get('is_active', 'on') == 'on'
        service.save()
        return redirect('service_list')
    return render(request, 'service_form.html', {'service': service})


def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        service.delete()
        return redirect('service_list')
    return render(request, 'service_confirm_delete.html', {'service': service})


def service_duplicate(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        new_service = Service.objects.create(
            name=service.name + ' (копия)',
            code=service.code + '_copy',
            description=service.description,
            unit=service.unit,
            is_active=service.is_active
        )
        return redirect('service_edit', pk=new_service.pk)
    return render(request, 'service_confirm_duplicate.html', {'service': service})


@csrf_exempt
def api_service_list(request):
    if request.method == 'GET':
        services = Service.objects.select_related('workshop').prefetch_related('service_materials__material').all()
        data = []
        for s in services:
            d = {
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'unit': s.unit,
                'workshop': s.workshop.id if s.workshop else None,
                'workshop_name': s.workshop.name if s.workshop else '',
                'service_price': float(s.service_price),
                'defect_penalty': float(s.defect_penalty),
                'is_active': s.is_active,
                'created_at': s.created_at,
                'updated_at': s.updated_at,
                'materials_info': [
                    {
                        'id': sm.material.id,
                        'name': str(sm.material),
                        'amount': float(sm.amount)
                    }
                    for sm in s.service_materials.all()
                ]
            }
            data.append(d)
        return JsonResponse({'status': 'success', 'data': data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_service_create(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # Преобразуем is_active в булево значение
        is_active = data.get('is_active', True)
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true'
        else:
            is_active = bool(is_active)
            
        service = Service.objects.create(
            name=data.get('name',''),
            description=data.get('description',''),
            unit=data.get('unit','услуга'),
            workshop_id=data.get('workshop'),
            service_price=data.get('service_price',0),
            defect_penalty=data.get('defect_penalty',0),
            is_active=is_active
        )
        
        # Добавляем материалы к услуге
        materials_data = data.get('materials', [])
        for mat_data in materials_data:
            if mat_data.get('id') and mat_data.get('amount'):
                ServiceMaterial.objects.create(
                    service=service,
                    material_id=mat_data['id'],
                    amount=mat_data['amount']
                )
        
        # Создаем собственный словарь для ответа
        response_data = {
            'id': service.id,
            'name': service.name,
            'description': service.description,
            'unit': service.unit,
            'workshop': service.workshop.id if service.workshop else None,
            'workshop_name': service.workshop.name if service.workshop else '',
            'service_price': float(service.service_price),
            'defect_penalty': float(service.defect_penalty),
            'is_active': service.is_active,
            'created_at': service.created_at.isoformat() if service.created_at else None,
            'updated_at': service.updated_at.isoformat() if service.updated_at else None,
            'materials_info': []
        }
        
        return JsonResponse({'status': 'success', 'data': response_data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_service_update(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'PUT':
        data = json.loads(request.body)
        
        # Обновляем основные поля
        fields_to_update = ['name', 'description', 'unit', 'workshop', 'service_price', 'defect_penalty', 'is_active']
        for field in fields_to_update:
            if field in data:
                if field == 'workshop':
                    service.workshop_id = data[field]
                elif field == 'is_active':
                    # Преобразуем строковое значение в булево
                    if isinstance(data[field], str):
                        service.is_active = data[field].lower() == 'true'
                    else:
                        service.is_active = bool(data[field])
                else:
                    setattr(service, field, data[field])
        
        service.save()
        
        # Обновляем материалы
        if 'materials' in data:
            # Удаляем старые связи с материалами
            service.service_materials.all().delete()
            
            # Добавляем новые материалы
            materials_data = data.get('materials', [])
            for mat_data in materials_data:
                if mat_data.get('id') and mat_data.get('amount'):
                    ServiceMaterial.objects.create(
                        service=service,
                        material_id=mat_data['id'],
                        amount=mat_data['amount']
                    )
        
        # Создаем собственный словарь для ответа
        response_data = {
            'id': service.id,
            'name': service.name,
            'description': service.description,
            'unit': service.unit,
            'workshop': service.workshop.id if service.workshop else None,
            'workshop_name': service.workshop.name if service.workshop else '',
            'service_price': float(service.service_price),
            'defect_penalty': float(service.defect_penalty),
            'is_active': service.is_active,
            'created_at': service.created_at.isoformat() if service.created_at else None,
            'updated_at': service.updated_at.isoformat() if service.updated_at else None,
            'materials_info': [
                {
                    'id': sm.material.id,
                    'name': str(sm.material),
                    'amount': float(sm.amount)
                }
                for sm in service.service_materials.all()
            ]
        }
        
        return JsonResponse({'status': 'success', 'data': response_data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'DELETE':
        service.delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_service_bulk_delete(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        ids = data.get('ids',[])
        Service.objects.filter(id__in=ids).delete()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_service_stats(request):
    if request.method == 'GET':
        qs = Service.objects.all()
        totalValue = qs.aggregate(total=Sum('service_price'))['total'] or 0
        totalItems = qs.count()
        activeServices = qs.filter(is_active=True).count()
        avgPrice = qs.aggregate(avg=Avg('service_price'))['avg'] or 0
        return JsonResponse({'status': 'success', 'data': {
            'totalValue': totalValue,
            'totalItems': totalItems,
            'activeServices': activeServices,
            'avgPrice': avgPrice
        }})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_service_duplicate(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        # Преобразуем is_active в булево значение
        is_active = service.is_active
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true'
        else:
            is_active = bool(is_active)
            
        new_service = Service.objects.create(
            name=service.name + ' (копия)',
            description=service.description,
            unit=service.unit,
            workshop=service.workshop,
            service_price=service.service_price,
            defect_penalty=service.defect_penalty,
            is_active=is_active
        )
        
        # Копируем материалы
        for sm in service.service_materials.all():
            ServiceMaterial.objects.create(
                service=new_service,
                material=sm.material,
                amount=sm.amount
            )
        
        # Создаем собственный словарь для ответа
        response_data = {
            'id': new_service.id,
            'name': new_service.name,
            'description': new_service.description,
            'unit': new_service.unit,
            'workshop': new_service.workshop.id if new_service.workshop else None,
            'workshop_name': new_service.workshop.name if new_service.workshop else '',
            'service_price': float(new_service.service_price),
            'defect_penalty': float(new_service.defect_penalty),
            'is_active': new_service.is_active,
            'created_at': new_service.created_at.isoformat() if new_service.created_at else None,
            'updated_at': new_service.updated_at.isoformat() if new_service.updated_at else None,
            'materials_info': [
                {
                    'id': sm.material.id,
                    'name': str(sm.material),
                    'amount': float(sm.amount)
                }
                for sm in new_service.service_materials.all()
            ]
        }
        
        return JsonResponse({'status': 'success', 'data': response_data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_materials(request):
    if request.method == 'GET':
        materials = RawMaterial.objects.all()
        data = [
            {'id': m.id, 'name': str(m)} for m in materials
        ]
        return JsonResponse({'status': 'success', 'data': data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_workshops(request):
    if request.method == 'GET':
        workshops = Workshop.objects.all()
        data = [{'id': w.id, 'name': w.name} for w in workshops]
        return JsonResponse({'status': 'success', 'data': data})
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
