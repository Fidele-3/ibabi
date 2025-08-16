# dashboards/views.py
from decimal import Decimal
from django.db.models import Count, Sum, Q
from django.db.models.functions import Coalesce
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# --- imports: align these to your apps ---
from users.models.customuser import CustomUser
from users.models.addresses import District, Sector, Cell
from users.models.products import Product  # ProductPrice/RecommendedQuantity not needed here

# If these are in a different app, update paths accordingly
from report.models import (
    Land,
    HarvestReport,
    LivestockLocation,
    LivestockAnimal,
    LivestockProduction,
    SeasonalCropPlan,
    DistrictInventory,
    CellInventory,
    CellResourceRequest,
    ResourceRequest,
    ResourceRequestFeedback,
    LandSeasonalAssignment,
)

class RoleAwareDashboard(APIView):
    permission_classes = [IsAuthenticated]

    # ------------- helpers -------------

    def _scope(self, user):
        """
        Returns a dict describing the geographic/ownership scope for queries.
        Keys used:
          - district (District or None)
          - sector   (Sector or None)
          - cell     (Cell or None)
          - owner    (CustomUser or None)  # for citizens
          - level    (str)                 # user_level
          - label    (str)                 # human-readable scope
        """
        level = user.user_level
        scope = {"district": None, "sector": None, "cell": None, "owner": None, "level": level, "label": "All"}

        if level == "super_admin":
            scope["label"] = "All"
            return scope

        if level == "district_officer":
            district = getattr(user, "managed_district", None)
            if not district:
                # Unassigned officer: show empty scope but label it
                scope["label"] = "Unassigned district"
                return scope
            scope.update(district=district, label=f"District: {district.name}")
            return scope

        if level == "sector_officer":
            sector = getattr(user, "managed_sector", None)
            if not sector:
                scope["label"] = "Unassigned sector"
                return scope
            scope.update(sector=sector, district=sector.district, label=f"Sector: {sector.name}")
            return scope

        if level == "cell_officer":
            cell = getattr(user, "managed_cell", None)
            if not cell:
                scope["label"] = "Unassigned cell"
                return scope
            scope.update(cell=cell, sector=cell.sector, district=cell.sector.district, label=f"Cell: {cell.name}")
            return scope

        # citizen (or any other user level defaults to own data)
        scope.update(owner=user, label=f"My data ({user.get_full_name()})")
        return scope

    def _apply_scope(self, qs, scope, *, model):
        """
        Applies the scope to a queryset based on model type.
        """
        level = scope["level"]
        district = scope["district"]
        sector = scope["sector"]
        cell = scope["cell"]
        owner = scope["owner"]

        # super_admin → no filter
        if level == "super_admin":
            return qs

        # citizens → owner/farmer filters
        if owner:
            if model is Land:
                return qs.filter(owner=owner)
            if model is HarvestReport:
                return qs.filter(farmer=owner)
            if model is LivestockLocation:
                return qs.filter(owner=owner)
            if model is LivestockAnimal:
                return qs.filter(livestock_location__owner=owner)
            if model is LivestockProduction:
                return qs.filter(farmer=owner)
            if model is SeasonalCropPlan:
                # citizen doesn't manage cells; show none
                return qs.none()
            if model is DistrictInventory:
                return qs.none()
            if model is CellInventory:
                return qs.none()
            if model is ResourceRequest:
                return qs.filter(farmer=owner)
            if model is CellResourceRequest:
                return qs.none()
            if model is ResourceRequestFeedback:
                return qs.filter(farmer=owner)
            if model is LandSeasonalAssignment:
                return qs.filter(land__owner=owner)
            return qs

        # geography for officers
        if district:
            # district_officer scope (and also sector/cell officers inherit a district)
            if model is Land:
                qs = qs.filter(district=district)
            elif model is HarvestReport:
                qs = qs.filter(land__district=district)
            elif model is LivestockLocation:
                qs = qs.filter(district=district)
            elif model is LivestockAnimal:
                qs = qs.filter(livestock_location__district=district)
            elif model is LivestockProduction:
                qs = qs.filter(location__district=district)
            elif model is SeasonalCropPlan:
                qs = qs.filter(cell__sector__district=district)
            elif model is DistrictInventory:
                qs = qs.filter(district=district)
            elif model is CellInventory:
                qs = qs.filter(district=district)
            elif model is ResourceRequest:
                qs = qs.filter(land__district=district)
            elif model is CellResourceRequest:
                qs = qs.filter(cell__sector__district=district)
            elif model is ResourceRequestFeedback:
                qs = qs.filter(request__land__district=district)
            elif model is LandSeasonalAssignment:
                qs = qs.filter(land__district=district)

        if sector:
            # narrow to sector
            if model is Land:
                qs = qs.filter(sector=sector)
            elif model is HarvestReport:
                qs = qs.filter(land__sector=sector)
            elif model is LivestockLocation:
                qs = qs.filter(sector=sector)
            elif model is LivestockAnimal:
                qs = qs.filter(livestock_location__sector=sector)
            elif model is LivestockProduction:
                qs = qs.filter(location__sector=sector)
            elif model is SeasonalCropPlan:
                qs = qs.filter(cell__sector=sector)
            elif model is CellInventory:
                qs = qs.filter(sector=sector)
            elif model is ResourceRequest:
                qs = qs.filter(land__sector=sector)
            elif model is CellResourceRequest:
                qs = qs.filter(cell__sector=sector)
            elif model is ResourceRequestFeedback:
                qs = qs.filter(request__land__sector=sector)
            elif model is LandSeasonalAssignment:
                qs = qs.filter(land__sector=sector)

        if cell:
            # narrow to cell
            if model is Land:
                qs = qs.filter(cell=cell)
            elif model is HarvestReport:
                qs = qs.filter(land__cell=cell)
            elif model is LivestockLocation:
                qs = qs.filter(cell=cell)
            elif model is LivestockAnimal:
                qs = qs.filter(livestock_location__cell=cell)
            elif model is LivestockProduction:
                qs = qs.filter(location__cell=cell)
            elif model is SeasonalCropPlan:
                qs = qs.filter(cell=cell)
            elif model is CellInventory:
                qs = qs.filter(cell=cell)
            elif model is ResourceRequest:
                qs = qs.filter(land__cell=cell)
            elif model is CellResourceRequest:
                qs = qs.filter(cell=cell)
            elif model is ResourceRequestFeedback:
                qs = qs.filter(request__land__cell=cell)
            elif model is LandSeasonalAssignment:
                qs = qs.filter(land__cell=cell)

        return qs

    # ------------- main -------------

    def get(self, request):
        user = request.user
        scope = self._scope(user)

        # Users (role-scoped)
        if user.user_level == "super_admin":
            user_counts = {
                "total_users": CustomUser.objects.count(),
                "citizens": CustomUser.objects.filter(user_level="citizen").count(),
                "cell_officers": CustomUser.objects.filter(user_level="cell_officer").count(),
                "sector_officers": CustomUser.objects.filter(user_level="sector_officer").count(),
                "district_officers": CustomUser.objects.filter(user_level="district_officer").count(),
            }
        elif user.user_level == "district_officer" and scope["district"]:
            d = scope["district"]
            user_counts = {
                "total_users": CustomUser.objects.filter(
                    Q(lands__district=d) |
                    Q(livestock_locations__district=d) |
                    Q(managed_cell__sector__district=d) |
                    Q(managed_sector__district=d) |
                    Q(managed_district=d)
                ).distinct().count(),
                "citizens": CustomUser.objects.filter(
                    user_level="citizen",
                    lands__district=d
                ).distinct().count(),
                "cell_officers": CustomUser.objects.filter(
                    user_level="cell_officer",
                    managed_cell__sector__district=d
                ).distinct().count(),
                "sector_officers": CustomUser.objects.filter(
                    user_level="sector_officer",
                    managed_sector__district=d
                ).distinct().count(),
                "district_officers": CustomUser.objects.filter(
                    user_level="district_officer",
                    managed_district=d
                ).distinct().count(),
            }
        elif user.user_level == "sector_officer" and scope["sector"]:
            s = scope["sector"]
            user_counts = {
                "total_users": CustomUser.objects.filter(
                    Q(lands__sector=s) |
                    Q(livestock_locations__sector=s) |
                    Q(managed_cell__sector=s) |
                    Q(managed_sector=s) |
                    Q(managed_district=s.district)
                ).distinct().count(),
                "citizens": CustomUser.objects.filter(
                    user_level="citizen", lands__sector=s
                ).distinct().count(),
                "cell_officers": CustomUser.objects.filter(
                    user_level="cell_officer", managed_cell__sector=s
                ).distinct().count(),
                "sector_officers": CustomUser.objects.filter(
                    user_level="sector_officer", managed_sector=s
                ).distinct().count(),
                "district_officers": CustomUser.objects.filter(
                    user_level="district_officer", managed_district=s.district
                ).distinct().count(),
            }
        elif user.user_level == "cell_officer" and scope["cell"]:
            c = scope["cell"]
            # citizens = owners with any Land or LivestockLocation in the cell
            citizens_q = CustomUser.objects.filter(
                user_level="citizen"
            ).filter(
                Q(lands__cell=c) | Q(livestock_locations__cell=c)
            ).distinct()
            user_counts = {
                "total_users": CustomUser.objects.filter(
                    Q(lands__cell=c) | Q(livestock_locations__cell=c) |
                    Q(managed_cell=c) | Q(managed_sector=c.sector) | Q(managed_district=c.sector.district)
                ).distinct().count(),
                "citizens": citizens_q.count(),
                "cell_officers": 1 if c.cell_officer_id else 0,
                "sector_officers": 1 if c.sector.sector_officer_id else 0,
                "district_officers": 1 if c.sector.district.district_officer_id else 0,
            }
        else:
            # citizen or unassigned officer → user counts not meaningful
            user_counts = None

        # Products by category (catalog-level — not geo-scoped)
        products_by_category = list(
            Product.objects.values("category").annotate(count=Count("id")).order_by("category")
        )
        total_products = sum(row["count"] for row in products_by_category)

        # Lands
        land_qs = self._apply_scope(Land.objects.all(), scope, model=Land)
        total_lands = land_qs.count()
        total_hectares = land_qs.aggregate(
            ha=Coalesce(Sum("size_hectares"), 0)
        )["ha"]

        # Harvest reports
        harvest_qs = self._apply_scope(HarvestReport.objects.all(), scope, model=HarvestReport)
        harvest_total = harvest_qs.count()
        harvest_qty = harvest_qs.aggregate(q=Coalesce(Sum("quantity"), 0.0))["q"]
        harvest_by_status = list(
            harvest_qs.values("stutus").annotate(count=Count("id"), quantity=Coalesce(Sum("quantity"), 0.0))
        )

        # Livestock
        livestock_loc_qs = self._apply_scope(LivestockLocation.objects.all(), scope, model=LivestockLocation)
        livestock_locations = livestock_loc_qs.count()

        livestock_animals_qs = self._apply_scope(LivestockAnimal.objects.all(), scope, model=LivestockAnimal)
        livestock_animal_records = livestock_animals_qs.count()
        livestock_total_animals = livestock_animals_qs.aggregate(
            qty=Coalesce(Sum("quantity"), 0)
        )["qty"]

        livestock_prod_qs = self._apply_scope(LivestockProduction.objects.all(), scope, model=LivestockProduction)
        livestock_productions = livestock_prod_qs.count()
        livestock_production_qty = livestock_prod_qs.aggregate(
            q=Coalesce(Sum("quantity"), 0.0)
        )["q"]
        livestock_prod_by_status = list(
            livestock_prod_qs.values("status").annotate(count=Count("id"), quantity=Coalesce(Sum("quantity"), 0.0))
        )

        # Seasonal planning
        plans_qs = self._apply_scope(SeasonalCropPlan.objects.all(), scope, model=SeasonalCropPlan)
        seasonal_plans = plans_qs.count()

        land_assign_qs = self._apply_scope(LandSeasonalAssignment.objects.all(), scope, model=LandSeasonalAssignment)
        land_assignments = land_assign_qs.count()

        # Inventories
        dist_inv_qs = self._apply_scope(DistrictInventory.objects.all(), scope, model=DistrictInventory)
        district_inventories = dist_inv_qs.count()
        district_inv_added = dist_inv_qs.aggregate(val=Coalesce(Sum("quantity_added"), 0))["val"]
        # sum remaining via Python because it's a property
        district_inv_remaining = sum((obj.quantity_remaining for obj in dist_inv_qs), 0.0)

        cell_inv_qs = self._apply_scope(CellInventory.objects.all(), scope, model=CellInventory)
        cell_inventories = cell_inv_qs.count()
        cell_inv_available = cell_inv_qs.aggregate(val=Coalesce(Sum("quantity_available"), 0))["val"]

        # Resource requests (farmer) + CellResourceRequest (cell)
        rr_qs = self._apply_scope(ResourceRequest.objects.all(), scope, model=ResourceRequest)
        rr_total = rr_qs.count()
        rr_by_status = list(rr_qs.values("status").annotate(count=Count("id")))

        crr_qs = self._apply_scope(CellResourceRequest.objects.all(), scope, model=CellResourceRequest)
        crr_total = crr_qs.count()
        crr_by_status = list(crr_qs.values("status").annotate(count=Count("id")))

        # Feedback
        fb_qs = self._apply_scope(ResourceRequestFeedback.objects.all(), scope, model=ResourceRequestFeedback)
        feedback_total = fb_qs.count()
        feedback_avg = fb_qs.aggregate(avg=Coalesce(Sum("rating"), 0))["avg"]
        if feedback_total:
            feedback_avg = float(feedback_avg) / float(feedback_total)
        else:
            feedback_avg = None

        return Response({
            "scope": scope["label"],
            "user_level": scope["level"],

            "user_counts": user_counts,

            "products": {
                "total": total_products,
                "by_category": products_by_category,
            },

            "land": {
                "total_parcels": total_lands,
                "total_hectares": float(total_hectares) if isinstance(total_hectares, Decimal) else total_hectares,
            },

            "harvest_reports": {
                "total": harvest_total,
                "total_quantity": harvest_qty,
                "by_status": harvest_by_status,   # [{'stutus': 'available', 'count': n, 'quantity': q}, ...]
            },

            "livestock": {
                "locations": livestock_locations,
                "animal_records": livestock_animal_records,
                "total_animals": livestock_total_animals,
                "productions": {
                    "total": livestock_productions,
                    "total_quantity": livestock_production_qty,
                    "by_status": livestock_prod_by_status,
                }
            },

            "seasonal_planning": {
                "seasonal_plans": seasonal_plans,
                "land_assignments": land_assignments,
            },

            "inventories": {
                "district": {
                    "records": district_inventories,
                    "quantity_added_total": district_inv_added,
                    "quantity_remaining_total": district_inv_remaining,
                },
                "cell": {
                    "records": cell_inventories,
                    "quantity_available_total": float(cell_inv_available) if isinstance(cell_inv_available, Decimal) else cell_inv_available,
                }
            },

            "resource_requests": {
                "farmer_requests": {
                    "total": rr_total,
                    "by_status": rr_by_status,
                },
                "cell_requests": {
                    "total": crr_total,
                    "by_status": crr_by_status,
                },
                "feedback": {
                    "total": feedback_total,
                    "avg_rating": feedback_avg,
                }
            },
        })
