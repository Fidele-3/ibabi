from rest_framework import generics, status
from rest_framework.response import Response
from users.serializer.super_admin_register_serializer import SuperAdminCreateSerializer
from users.models import CustomUser
from rest_framework.permissions import AllowAny
class SuperAdminCreateView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = SuperAdminCreateSerializer

    def create(self, request, *args, **kwargs):
        if CustomUser.objects.filter(user_level='super_admin').exists():
            return Response({"detail": "Superadmin already exists."}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)
