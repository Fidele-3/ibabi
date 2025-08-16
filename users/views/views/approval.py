from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from users.serializer.resources import ResourceRequestDetailSerializer, ResourceRequestStatusUpdateSerializer
from report.models import ResourceRequest
from users.models.addresses import Cell  # to query cells if needed

class ResourceRequestStatusViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ResourceRequest.objects.select_related(
        "land", "land__cell", "land__cell__sector", "land__cell__sector__district", "product"
    )

    def get_serializer_class(self):
        if self.action in ['partial_update']:
            return ResourceRequestStatusUpdateSerializer
        return ResourceRequestDetailSerializer

    def get_queryset(self):
        user = self.request.user

        if user.user_level == "super_admin":
            return self.queryset

        if user.user_level == "district_officer":
            return self.queryset.filter(
                land__cell__sector__district=user.managed_district
            )

        if user.user_level == "cell_officer":
            return self.queryset.filter(
                land__cell=user.managed_cell
            )

        return self.queryset.filter(farmer=user)

    def partial_update(self, request, pk=None):
        user = request.user
        instance = get_object_or_404(self.get_queryset(), pk=pk)

        if user.user_level != "cell_officer":
            return Response(
                {"detail": "Only cell officers can update the status of a request."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(
            instance=instance,
            data=request.data,
            partial=True,
            context={"request_obj": instance, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(ResourceRequestDetailSerializer(instance).data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        instance = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
