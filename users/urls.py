from django.urls import path, include
from users.views.views.announcements import AnnouncementViewSet
from users.views.views.citizen_register import CitizenRegistrationView
from users.views.views.super_admin_creation_view import SuperAdminCreateView
from users.views.views.login import LoginAPIView, OTPVerifyAPIView
from users.views.views.products import (
    ProductViewSet,
    ProductPriceViewSet,
    RecommendedQuantityViewSet,
    HarvestReportViewSet,
    LivestockProductionViewSet
)
from users.views.views.create_admin import (
    DistrictOfficerViewSet,
    CellOfficerViewSet,
    TechnicianViewSet
)
from users.views.views.reset_password import (
    RequestPasswordResetOTPView,
    VerifyResetOTPView,
    ResetPasswordView,
    AuthenticatedChangePasswordView
)
from .views.views.resources import (
    DistrictInventoryViewSet,
    CellInventoryViewSet,
    ResourceRequestViewSet,
    ResourceRequestFeedbackViewSet,
)
from users.views.views.profile import MeViewSet
from users.views.views.adresses import get_districts, get_sectors, get_cells, get_villages, get_provinces, get_available_districts, get_available_cells
from users.views.views.land import LandViewSet, LivestockLocationViewSet
from users.views.views.season_plan import CellSeasonPlanViewSet
from users.views.views.approval import ResourceRequestStatusViewSet
from users.views.views.inventory import CellResourceRequestListView, CellResourceRequestCreateView, CellInventoryViewSets, DistrictInventoryViewSets
from users.views.views.reply import  CellResourceRequestViewSet
from rest_framework.routers import DefaultRouter
from users.views.views.issues import FarmerIssueViewSet
from users.views.views.notifications import NotificationViewSet
from users.views.views.dashbord import RoleAwareDashboard
from users.views.views.cell_climate import CellClimateDataViewSet
from users.views.views.ai_data import AIDataViewSet
from users.views.api_views.citizen_logout import LogoutView
from users.views.views.farmer_inventory import FarmerInventoryViewSet
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'product-prices', ProductPriceViewSet, basename='productprice')
router.register(r'recommended-quantities', RecommendedQuantityViewSet, basename='recommendedquantity') #GET, POST, PATCH, DELETE 
router.register(r'harvest-reports', HarvestReportViewSet, basename='harvestreport')#GET, POST, PATCH, DELETE HARVEST REPORTS
router.register(r'livestock-productions', LivestockProductionViewSet, basename='livestockproduction')#GET, POST, PATCH, DELETE LIVESTOCK REPORTS
router.register(r'district-officers', DistrictOfficerViewSet, basename='district-officer')#GET, POST, PATCH, DELETE 
router.register(r'cell-officers', CellOfficerViewSet, basename='cell-officer')#GET, POST, PATCH, DELETE 
router.register(r'technicians', TechnicianViewSet, basename='technician')#GET, POST, PATCH, DELETE 
#SPECIAL CASE FOR THE VIEWS ENPOINTS BELOW
#router.register(r'district-inventories', DistrictInventoryViewSet, basename='districtinventory')
#router.register(r'cell-inventories', CellInventoryViewSet, basename='cellinventory')
router.register(r'resource-requests', ResourceRequestViewSet, basename='resourcerequest') #GET ONLY VIEW RESOURCE REQUESTS MADE BY CITIZENS
router.register(r'resource-request-feedbacks', ResourceRequestFeedbackViewSet, basename='requestfeedback') # GET, POST, PATCH. FEEDBACK ON RESOURCE REQUESTS
router.register(r'cell-season-plans', CellSeasonPlanViewSet, basename='cell-season-plan')#POST, GET, PATCH, DELETE CELL SEASON PLANS (if season has started, unSafe methods doesn't work)
router.register(r'lands', LandViewSet, basename='land')#GET, POST, PATCH, DELETE LAND DETAILS
router.register(r'livestocks', LivestockLocationViewSet, basename='livestocklocation') #POST, GET, PATCH. ADD LIVESTOCK AND ITS LOCATION
router.register(r'resource-request-status', ResourceRequestStatusViewSet, basename='resourcerequeststatus') # APPROVE THE REQUEST MADE BY CITIZENS FOR RESOURCES
router.register(r'district-inventory', DistrictInventoryViewSets, basename='district-inventory') # VIEW DISTRICT INVENTORY AND PERFORM UPDATES
router.register(r'cell-inventory', CellInventoryViewSets, basename='cell-inventory')#GET, POST VIEW CELL INVENTORY AND PERFORM UPDATES
router.register(r'cell-resource-reply', CellResourceRequestViewSet, basename='cell-resource-request') # PATCH(pass the inventory id) VIEW CELL RESOURCE REQUESTS AND PERFORM UPDATES, PATCH WITH ID 
router.register(r'farmer-issues', FarmerIssueViewSet, basename='farmerissue')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'announcements', AnnouncementViewSet, basename='announcements')
router.register(r'cell-climates', CellClimateDataViewSet, basename='cellclimate')
router.register(r'farmer-inventory', FarmerInventoryViewSet, basename='farmer-inventory') # http://localhost:8000/api/farmer-inventory/08ec6d3a-1912-41e3-819a-ecacc6938546/deduct/
me_viewset = MeViewSet.as_view({
    "get": "list",
    "put": "update",
    "patch": "partial_update",
})
router.register(r'ai-data', AIDataViewSet, basename='ai-data') # http://localhost:8000//api/ai-data/?page=1&page_size=100&year=2025&month=8
urlpatterns = [
    path('super-admin/register/', SuperAdminCreateView.as_view(), name='super_admin_create'),
    path('auth/login/', LoginAPIView.as_view(), name='login'),
    path('auth/verify-otp/', OTPVerifyAPIView.as_view(), name='verify-otp'),
    path('register/citizen/', CitizenRegistrationView.as_view(), name='register-citizen'),
    path('cell-resource-requests/', CellResourceRequestListView.as_view(), name='cellresource-list'),
    path('cell-resource-requests/create/', CellResourceRequestCreateView.as_view(), name='cellresource-create'),

    # Password reset & change endpoints
    path('auth/password-reset/request-otp/', RequestPasswordResetOTPView.as_view(), name='request-password-reset-otp'),
    path('auth/password-reset/verify-otp/', VerifyResetOTPView.as_view(), name='verify-password-reset-otp'),
    path('auth/password-reset/', ResetPasswordView.as_view(), name='reset-password'),
    path('auth/password-change/', AuthenticatedChangePasswordView.as_view(), name='change-password'),
    path("dashboard/", RoleAwareDashboard.as_view(), name="dashboard"),
    path('ajax/get-districts/', get_districts, name='get_districts'),
    path('ajax/get-sectors/', get_sectors, name='get_sectors'),
    path('ajax/get-provinces/', get_provinces, name='get_provinces'),
    path('ajax/get-cells/', get_cells, name='get_cells'),
    path('ajax/get-villages/', get_villages, name='get_villages'),
    path('ajax/get-available-districts/', get_available_districts, name='get_available_districts'),
    path('ajax/get-available-cells/', get_available_cells, name='get_available_cells'),
    path('logout/', LogoutView.as_view(), name='logout'),  # Logout endpoint
    path('me/', me_viewset, name='me'),  # User profile endpoint


    path('', include(router.urls)),
]
