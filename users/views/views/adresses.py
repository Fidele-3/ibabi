from django.http import JsonResponse
from users.models.addresses import Province, District, Sector, Cell, Village

# Existing endpoints remain unchanged
def get_provinces(request):
    provinces = Province.objects.all().values('id', 'name')
    return JsonResponse({'provinces': list(provinces)})

def get_districts(request):
    province_id = request.GET.get('province_id')
    districts = District.objects.filter(province_id=province_id).values('id', 'name')
    return JsonResponse({'districts': list(districts)})

def get_sectors(request):
    district_id = request.GET.get('district_id')
    sectors = Sector.objects.filter(district_id=district_id).values('id', 'name')
    return JsonResponse({'sectors': list(sectors)})

def get_cells(request):
    sector_id = request.GET.get('sector_id')
    cells = Cell.objects.filter(sector_id=sector_id).values('id', 'name')
    return JsonResponse({'cells': list(cells)})

def get_villages(request):
    cell_id = request.GET.get('cell_id')
    villages = Village.objects.filter(cell_id=cell_id).values('id', 'name')
    return JsonResponse({'villages': list(villages)})

# --- NEW ENDPOINTS ---

def get_available_districts(request):
    province_id = request.GET.get('province_id')
    # Only districts without a district_officer
    districts = District.objects.filter(province_id=province_id, district_officer__isnull=True).values('id', 'name')
    return JsonResponse({'districts': list(districts)})

def get_available_cells(request):
    sector_id = request.GET.get('sector_id')
    # Only cells without a cell_officer
    cells = Cell.objects.filter(sector_id=sector_id, cell_officer__isnull=True).values('id', 'name')
    return JsonResponse({'cells': list(cells)})
