# dashboards/views.py
from decimal import Decimal
from django.db.models import  Q
from django.db.models.functions import Coalesce
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, DecimalField, FloatField, IntegerField
from django.db.models.functions import Coalesce
from users.models.addresses import District, Sector, Cell
from report.models import FarmerIssue, FarmerIssueReply

from users.models.customuser import CustomUser
from users.models.products import Product  
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
            if model is Cell:  # seasonal planning is now on Cell
                return qs.none()
            if model is ResourceRequest:
                return qs.filter(farmer=owner)
            if model is ResourceRequestFeedback:
                return qs.filter(farmer=owner)
            if model is FarmerIssue:
                return qs.filter(farmer=owner)
            if model is FarmerIssueReply:
                return qs.filter(issue__farmer=owner)
            return qs

        # geography for officers
        if district:
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
            elif model is Cell:
                qs = qs.filter(sector__district=district)
            elif model is ResourceRequest:
                qs = qs.filter(land__district=district)
            elif model is ResourceRequestFeedback:
                qs = qs.filter(request__land__district=district)
            elif model is FarmerIssue:
                qs = qs.filter(district=district)
            elif model is FarmerIssueReply:
                qs = qs.filter(issue__district=district)

        if sector:
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
            elif model is Cell:
                qs = qs.filter(sector=sector)
            elif model is ResourceRequest:
                qs = qs.filter(land__sector=sector)
            elif model is ResourceRequestFeedback:
                qs = qs.filter(request__land__sector=sector)
            elif model is FarmerIssue:
                qs = qs.filter(sector=sector)
            elif model is FarmerIssueReply:
                qs = qs.filter(issue__sector=sector)

        if cell:
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
            elif model is Cell:
                qs = qs.filter(id=cell.id if hasattr(cell, "id") else cell)
            elif model is ResourceRequest:
                qs = qs.filter(land__cell=cell)
            elif model is ResourceRequestFeedback:
                qs = qs.filter(request__land__cell=cell)
            elif model is FarmerIssue:
                qs = qs.filter(cell=cell)
            elif model is FarmerIssueReply:
                qs = qs.filter(issue__cell=cell)

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
            Product.objects.values("category")
            .annotate(total=Count("id"))
            .order_by("category")
        )
        CATEGORY_CHOICES = dict(Product.CATEGORY_CHOICES)
        for item in products_by_category:
            item["category_display"] = CATEGORY_CHOICES.get(item["category"], item["category"])

        total_products = sum(row["total"] for row in products_by_category)


        

        # Lands
        land_qs = self._apply_scope(Land.objects.all(), scope, model=Land)
        total_lands = land_qs.count()
        total_hectares = land_qs.aggregate(
            ha=Coalesce(Sum("size_hectares"), 0, output_field=DecimalField())
        )["ha"]

        # Harvest reports
        harvest_qs = self._apply_scope(HarvestReport.objects.all(), scope, model=HarvestReport)
        harvest_total = harvest_qs.count()
        harvest_qty = harvest_qs.aggregate(
            q=Coalesce(Sum("quantity"), 0.0, output_field=FloatField())
        )["q"]
        harvest_by_status = list(
            harvest_qs.values("status").annotate(
                count=Count("id"),
                quantity=Coalesce(Sum("quantity"), 0.0, output_field=FloatField())
            )
        )

        # ----------------------------
        # LIVESTOCK SUMMARY
        # ----------------------------
        livestock_location_qs = self._apply_scope(
            LivestockLocation.objects.all(),
            scope,
            model=LivestockLocation
        )
        livestock_total_locations = livestock_location_qs.count()

        livestock_total_animals = LivestockAnimal.objects.filter(
            livestock_location__in=livestock_location_qs
        ).aggregate(
            total=Coalesce(Sum("quantity"), 0, output_field=IntegerField())
        )["total"]

        # Optional: total products per location
        livestock_total_products = livestock_location_qs.annotate(
            product_count=Count("products")
        ).aggregate(
            total=Coalesce(Sum("product_count"), 0, output_field=IntegerField())
        )["total"]

        livestock_summary = {
            "total": livestock_total_locations,
            "total_animals": livestock_total_animals,
            "total_products(If_any)": livestock_total_products
        }

        # ----------------------------
        # LIVESTOCK PRODUCTIONS
        # ----------------------------
        livestock_prod_qs = self._apply_scope(
            LivestockProduction.objects.all(),
            scope,
            model=LivestockProduction
        )

        livestock_productions_total = livestock_prod_qs.count()
        livestock_productions_qty = livestock_prod_qs.aggregate(
            q=Coalesce(Sum("quantity"), 0.0, output_field=FloatField())
        )["q"]

        livestock_productions_by_status = list(
            livestock_prod_qs.values("status").annotate(
                count=Count("id"),
                quantity=Coalesce(Sum("quantity"), 0.0, output_field=FloatField())
            )
        )

        livestock_productions_data = {
            "total": livestock_productions_total,
            "total_quantity": livestock_productions_qty,
            "by_status": livestock_productions_by_status
        }

        

        # Seasonal planning
        current_season = Cell.get_current_season()
        current_year = Cell.get_current_season_year()

        # Cells with seasonal plans (with crop info)
        seasonal_plans_qs = self._apply_scope(
            Cell.objects.filter(
                season=current_season,
                season_year=current_year,
                planned_crop__isnull=False
            ).select_related("planned_crop"),
            scope,
            model=Cell
        )

        # Count of plans
        seasonal_plans = seasonal_plans_qs.count()

        # List of plans with season & crop planned
        seasonal_plan_details = list(seasonal_plans_qs.values(
            "id",
            "name",
            "season",
            "season_year",
            "planned_crop__id",
            "planned_crop__name"
        ))

        # Lands in those cells
        land_qs = self._apply_scope(
            Land.objects.filter(cell__in=seasonal_plans_qs),
            scope,
            model=Land
        )

        land_assignments = land_qs.count()
        land_total_hectares = land_qs.aggregate(
            total_hectares=Sum("size_hectares")
        )["total_hectares"] or 0
        # Inventories
        dist_inv_qs = self._apply_scope(DistrictInventory.objects.all(), scope, model=DistrictInventory)
        district_inventories = dist_inv_qs.count()
        district_inv_added = dist_inv_qs.aggregate(
            val=Coalesce(Sum("quantity_added"), 0.0, output_field=FloatField())
        )["val"]

        district_inv_remaining = sum((obj.quantity_remaining for obj in dist_inv_qs), 0.0)

        cell_inv_qs = self._apply_scope(CellInventory.objects.all(), scope, model=CellInventory)
        cell_inventories = cell_inv_qs.count()
        cell_inv_available = cell_inv_qs.aggregate(
            val=Coalesce(Sum("quantity_available"), 0.0, output_field=FloatField())
        )["val"]

        # Resource requests
        rr_qs = self._apply_scope(ResourceRequest.objects.all(), scope, model=ResourceRequest)
        rr_total = rr_qs.count()
        rr_by_status = list(rr_qs.values("status").annotate(count=Count("id")))

        crr_qs = self._apply_scope(CellResourceRequest.objects.all(), scope, model=CellResourceRequest)
        crr_total = crr_qs.count()
        crr_by_status = list(crr_qs.values("status").annotate(count=Count("id")))

        # Feedback
        fb_qs = self._apply_scope(ResourceRequestFeedback.objects.all(), scope, model=ResourceRequestFeedback)
        feedback_total = fb_qs.count()
        feedback_avg = fb_qs.aggregate(
            avg=Coalesce(Sum("rating"), 0.0, output_field=FloatField())
        )["avg"]

        if feedback_total:
            feedback_avg = float(feedback_avg) / float(feedback_total)
        else:
            feedback_avg = None


        
        #ISSUES

        # Filter issues with your scope logic
        issues_qs = self._apply_scope(
            FarmerIssue.objects.all(),
            scope,
            model=FarmerIssue
        )

        # Status counts
        status_counts = issues_qs.aggregate(
            pending=Count("id", filter=Q(status__iexact="Pending")),
            resolved=Count("id", filter=Q(status__iexact="Resolved")),
            approved=Count("id", filter=Q(status__iexact="Approved")),
        )

        # Reply counts
        replied_counts = issues_qs.annotate(reply_count=Count("replies")).aggregate(
            with_reply=Count("id", filter=Q(reply_count__gt=0)),
            without_reply=Count("id", filter=Q(reply_count=0)),
        )

        # Optional: detailed list if needed
        issues_details = list(
            issues_qs.values(
                "id",
                "issue_type",
                "status",
                "farmer__full_names",
                "reported_at",
            )
        )



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
                "by_status": harvest_by_status,   # [{'status': 'available', 'count': n, 'quantity': q}, ...]
            },

            
            "livestock": livestock_summary,
            "livestock_productions": livestock_productions_data,
        
            "seasonal_planning": {
                "season": current_season,
                "season_year": current_year,
                "seasonal_plans": seasonal_plans,
                "seasonal_plan_details": seasonal_plan_details,
                "land_assignments": land_assignments,
                "total_land_hectares": float(land_total_hectares) if isinstance(land_total_hectares, Decimal) else land_total_hectares,
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
            "farmer_issues": {
                "total_issues": issues_qs.count(),
                "status_counts": status_counts,
                "reply_counts": replied_counts,
                "approved_issues": status_counts["approved"],
                "issues_details": issues_details,  # Optional for table display
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
