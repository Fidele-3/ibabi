import re
import logging
from rest_framework import serializers
from django.core.validators import RegexValidator, URLValidator
from django.utils import timezone
from users.models.customuser import CustomUser
from users.models.userprofile import UserProfile
from users.models.addresses import Province, District, Sector, Cell, Village

logger = logging.getLogger(__name__)


def _normalize_rwandan_phone(value: str) -> str:
    logger.debug(f"Normalizing phone input: {value}")

    if not value:
        logger.error("Empty phone number provided.")
        raise serializers.ValidationError("Empty phone number.")

    v = value.strip()
    has_plus = v.startswith('+')
    digits_only = re.sub(r'\D', '', v)
    logger.debug(f"Digits only: {digits_only}, has_plus: {has_plus}")

    if digits_only.startswith('0'):
        if len(digits_only) != 10 or not digits_only.startswith('07'):
            logger.error("Invalid local phone format")
            raise serializers.ValidationError("Local phone must be 10 digits and start with '07'.")
        normalized = '+250' + digits_only[1:]
    elif digits_only.startswith('250'):
        if len(digits_only) != 12 or not digits_only.startswith('2507'):
            logger.error("Invalid phone with 250 country code")
            raise serializers.ValidationError("Phone with country code must be 12 digits starting with '2507'.")
        normalized = '+' + digits_only
    elif has_plus and digits_only.startswith('250'):
        if len(digits_only) != 12:
            logger.error("Invalid +250 format")
            raise serializers.ValidationError("Phone with country code must be 12 digits (e.g. +250788123456).")
        normalized = '+' + digits_only
    elif len(digits_only) == 9 and digits_only.startswith('7'):
        normalized = '+250' + digits_only
    else:
        logger.error("Phone did not match any valid format")
        raise serializers.ValidationError(
            "Enter a valid Rwandan phone number. Allowed: '+2507...', '2507...', or '07...'."
        )

    if not re.match(r'^\+2507\d{8}$', normalized):
        logger.error(f"Normalization failed, got: {normalized}")
        raise serializers.ValidationError("Normalized phone must match +2507XXXXXXXX format.")

    logger.debug(f"Final normalized phone: {normalized}")
    return normalized


class UserProfileSerializer(serializers.ModelSerializer):
    website = serializers.URLField(
        required=False,
        allow_blank=True,
        validators=[URLValidator()],
        error_messages={"invalid": "Enter a valid website URL starting with http:// or https://"}
    )
    work_description = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = UserProfile
        fields = [
            "bio", "gender", "date_of_birth", "work", "work_description",
            "province", "district", "sector", "cell", "village", "website",
            "profile_picture"
        ]

    def validate_date_of_birth(self, value):
        logger.debug(f"Validating date_of_birth: {value}")
        if value and value > timezone.now().date():
            logger.error("Date of birth is in the future")
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value

    def validate(self, data):
        logger.debug(f"Validating profile relationships: {data}")
        province = data.get("province")
        district = data.get("district")
        sector = data.get("sector")
        cell = data.get("cell")
        village = data.get("village")

        if district and province and district.province != province:
            logger.error("District/province mismatch")
            raise serializers.ValidationError({"district": "Selected district does not belong to the selected province."})

        if sector and district and sector.district != district:
            logger.error("Sector/district mismatch")
            raise serializers.ValidationError({"sector": "Selected sector does not belong to the selected district."})

        if cell and sector and cell.sector != sector:
            logger.error("Cell/sector mismatch")
            raise serializers.ValidationError({"cell": "Selected cell does not belong to the selected sector."})

        if village and cell and village.cell != cell:
            logger.error("Village/cell mismatch")
            raise serializers.ValidationError({"village": "Selected village does not belong to the selected cell."})

        return data


class CitizenRegistrationSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()

    email = serializers.EmailField(
        error_messages={"invalid": "Enter a valid email address."}
    )
    phone_number = serializers.CharField()
    national_id = serializers.CharField(
        validators=[RegexValidator(
            regex=r'^\d{16}$',
            message="National ID must be exactly 16 digits."
        )]
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={
            "min_length": "Password must be at least 8 characters long."
        }
    )

    class Meta:
        model = CustomUser
        fields = [
            "email", "full_names", "phone_number", "national_id",
            "password", "profile"
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_email(self, value):
        logger.debug(f"Validating email: {value}")
        if CustomUser.objects.filter(email=value).exists():
            logger.error(f"Email already exists: {value}")
            raise serializers.ValidationError("Email is already registered.")
        return value

    def validate_phone_number(self, value):
        logger.debug(f"Validating phone_number: {value}")
        normalized = _normalize_rwandan_phone(value)
        if CustomUser.objects.filter(phone_number=normalized).exists():
            logger.error(f"Phone already exists: {normalized}")
            raise serializers.ValidationError("Phone number is already registered.")
        return normalized

    def validate_national_id(self, value):
        logger.debug(f"Validating national_id: {value}")
        if CustomUser.objects.filter(national_id=value).exists():
            logger.error(f"National ID already exists: {value}")
            raise serializers.ValidationError("National ID is already registered.")
        return value

    def create(self, validated_data):
        logger.debug(f"Creating user with validated_data: {validated_data}")
        profile_data = validated_data.pop("profile", {})
        try:
            user = CustomUser.objects.create_user(
                **validated_data,
                user_level="citizen"
            )
            logger.debug(f"User created: {user.id}, email={user.email}")
        except Exception as e:
            logger.exception("Error while creating CustomUser")
            raise

        try:
            UserProfile.objects.create(user=user, **profile_data)
            logger.debug(f"Profile created for user {user.id}")
        except Exception as e:
            logger.exception(f"Error while creating UserProfile for user {user.id}")
            raise

        return user
