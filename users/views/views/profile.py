from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from users.serializer.profile import UserSerializer
import traceback


class MeViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """GET /api/me/ → get current user details"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def update(self, request, pk=None):
        """PUT /api/me/ → update current user details"""
        return self._handle_update(request, partial=False)

    def partial_update(self, request, pk=None):
        """PATCH /api/me/ → partial update"""
        return self._handle_update(request, partial=True)

    def _handle_update(self, request, partial=False):
        """
        Handles update/partial_update and ensures all errors are sent to frontend.
        """
        serializer = UserSerializer(request.user, data=request.data, partial=partial)
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except ValidationError as ve:
            # Directly pass serializer errors to frontend
            return Response({"errors": ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Catch-all for unexpected exceptions
            return Response(
                {
                    "errors": {"non_field_error": str(e)},
                    "traceback": traceback.format_exc(),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
