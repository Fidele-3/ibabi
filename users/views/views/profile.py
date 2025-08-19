# user/views.py
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from users.serializer.profile import UserSerializer


class MeViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """GET /api/me/ → get current user details"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def update(self, request, pk=None):
        """PUT /api/me/ → update current user details"""
        serializer = UserSerializer(request.user, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        """PATCH /api/me/ → partial update"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
