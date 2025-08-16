from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from users.models import CustomUser, UserProfile
from users.models.addresses import Province, District, Sector, Cell, Village
from django.utils import timezone
import re

# Same normalization logic from CitizenRegistrationSerializer
def _normalize_rwandan_phone(value: str) -> str:
    if not value:
        raise serializers.ValidationError("Empty phone number.")

    v = value.strip()
    has_plus = v.startswith('+')
    digits_only = re.sub(r'\D', '', v)

    if digits_only.startswith('0'):
        if len(digits_only) != 10 or not digits_only.startswith('07'):
            raise serializers.ValidationError("Local phone must be 10 digits and start with '07'.")
        normalized = '+250' + digits_only[1:]
    elif digits_only.startswith('250'):
        if len(digits_only) != 12 or not digits_only.startswith('2507'):
            raise serializers.ValidationError("Phone with country code must be 12 digits starting with '2507'.")
        normalized = '+' + digits_only
    elif has_plus and digits_only.startswith('250'):
        if len(digits_only) != 12:
            raise serializers.ValidationError("Phone with country code must be 12 digits (e.g. +250788123456).")
        normalized = '+' + digits_only
    elif len(digits_only) == 9 and digits_only.startswith('7'):
        normalized = '+250' + digits_only
    else:
        raise serializers.ValidationError(
            "Enter a valid Rwandan phone number. Allowed: '+2507...', '2507...', or '07...'."
        )

    if not re.match(r'^\+2507\d{8}$', normalized):
        raise serializers.ValidationError("Normalized phone must match +2507XXXXXXXX format.")

    return normalized

class AdminCreateSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(write_only=True, required=False)
    profile = serializers.JSONField(write_only=True)

    managed_district_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    managed_sector_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    managed_cell_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    email = serializers.EmailField(error_messages={"invalid": "Enter a valid email address."})
    phone_number = serializers.CharField()
    national_id = serializers.CharField(
        validators=[RegexValidator(regex=r'^\d{16}$', message="National ID must be exactly 16 digits.")]
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={"min_length": "Password must be at least 8 characters long."}
    )

    class Meta:
        model = CustomUser
        fields = [
            "email",
            "full_names",
            "phone_number",
            "national_id",
            "user_level",
            "profile",
            "profile_picture",
            "managed_district_id",
            "managed_sector_id",
            "managed_cell_id",
            "password",
        ]
        extra_kwargs = {
            "user_level": {"read_only": True},
            "password": {"write_only": True},
        }

    # ---- Validations ----
    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def validate_phone_number(self, value):
        normalized = _normalize_rwandan_phone(value)
        if CustomUser.objects.filter(phone_number=normalized).exists():
            raise serializers.ValidationError("Phone number is already registered.")
        return normalized

    def validate_national_id(self, value):
        if CustomUser.objects.filter(national_id=value).exists():
            raise serializers.ValidationError("National ID is already registered.")
        return value

    def validate(self, data):
        user_level = data.get("user_level")

        if user_level == "district_officer" and not data.get("managed_district_id"):
            raise ValidationError("managed_district_id is required for district_officer")
        if user_level == "sector_officer" and not data.get("managed_sector_id"):
            raise ValidationError("managed_sector_id is required for sector_officer")
        if user_level == "cell_officer" and not data.get("managed_cell_id"):
            raise ValidationError("managed_cell_id is required for cell_officer")

        def check_officer_exists(model, id_val, officer_field_name):
            if id_val is None:
                return
            try:
                obj = model.objects.get(id=id_val)
            except model.DoesNotExist:
                raise ValidationError(f"{model.__name__} with id '{id_val}' does not exist.")
            if getattr(obj, officer_field_name) is not None:
                raise ValidationError(f"This {model.__name__.lower()} already has a {officer_field_name.replace('_', ' ')}.")

        if user_level == "district_officer":
            check_officer_exists(District, data.get("managed_district_id"), "district_officer")

        if user_level == "sector_officer":
            check_officer_exists(Sector, data.get("managed_sector_id"), "sector_officer")

        if user_level == "cell_officer":
            check_officer_exists(Cell, data.get("managed_cell_id"), "cell_officer")

        return data

    # ---- Creation ----
    def create(self, validated_data):
        profile_data = validated_data.pop("profile", {})
        profile_picture = validated_data.pop("profile_picture", None)
        managed_district_id = validated_data.pop("managed_district_id", None)
        managed_sector_id = validated_data.pop("managed_sector_id", None)
        managed_cell_id = validated_data.pop("managed_cell_id", None)

        user_level = validated_data.get("user_level")
        password = validated_data.pop("password", None)

        user = CustomUser.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()

        # Attach related addresses in profile data
        def get_address_instance(model, id_val):
            return model.objects.get(id=id_val) if id_val else None

        for field_name, model_class in [
            ("province", Province),
            ("district", District),
            ("sector", Sector),
            ("cell", Cell),
            ("village", Village),
        ]:
            if field_name in profile_data:
                profile_data[field_name] = get_address_instance(model_class, profile_data[field_name])

        # Create UserProfile
        user_profile = UserProfile.objects.create(user=user, **profile_data)
        if profile_picture:
            user_profile.profile_picture = profile_picture
            user_profile.save()

        # Assign officer roles
        if user_level == "district_officer":
            district = District.objects.get(id=managed_district_id)
            district.district_officer = user
            district.save()

        elif user_level == "sector_officer":
            sector = Sector.objects.get(id=managed_sector_id)
            sector.sector_officer = user
            sector.save()

        elif user_level == "cell_officer":
            cell = Cell.objects.get(id=managed_cell_id)
            cell.cell_officer = user
            cell.save()

        return user
