from rest_framework import generics, permissions
from users.serializer.citizen_register import CitizenRegistrationSerializer
from rest_framework.authentication import BasicAuthentication

class CitizenRegistrationView(generics.CreateAPIView):
    serializer_class = CitizenRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes = []  