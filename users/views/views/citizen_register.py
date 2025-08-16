from rest_framework import generics, permissions
from users.serializer.citizen_register import CitizenRegistrationSerializer

class CitizenRegistrationView(generics.CreateAPIView):
    serializer_class = CitizenRegistrationSerializer
    permission_classes = [permissions.AllowAny]  # Open to public for signup
