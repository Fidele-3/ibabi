def filter_by_role_and_location(qs, user):
    """
    Filters a queryset based on user role and location.
    Works for both dashboard widgets and viewsets.
    """

    if getattr(user, "is_super_admin", False):
        return qs

    if hasattr(user, "managed_cell") and user.managed_cell:
        # Detect if queryset is HarvestReport or LivestockProduction to filter correctly
        model = qs.model
        if model.__name__ == "HarvestReport":
            return qs.filter(land__cell=user.managed_cell)
        elif model.__name__ == "LivestockProduction":
            return qs.filter(location__cell=user.managed_cell)
        else:
            return qs.filter(cell=user.managed_cell)

    elif hasattr(user, "managed_sector") and user.managed_sector:
        model = qs.model
        if model.__name__ == "HarvestReport":
            return qs.filter(land__sector=user.managed_sector)
        elif model.__name__ == "LivestockProduction":
            return qs.filter(location__sector=user.managed_sector)
        else:
            return qs.filter(sector=user.managed_sector)

    elif hasattr(user, "managed_district") and user.managed_district:
        model = qs.model
        if model.__name__ == "HarvestReport":
            return qs.filter(land__district=user.managed_district)
        elif model.__name__ == "LivestockProduction":
            return qs.filter(location__district=user.managed_district)
        else:
            return qs.filter(district=user.managed_district)

    else:
        return qs.filter(farmer=user)
