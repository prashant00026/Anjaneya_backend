from rest_framework import serializers

from .models import Enquiry


class EnquiryCreateSerializer(serializers.ModelSerializer):
    # Honeypot: legitimate clients leave this empty.
    website = serializers.CharField(
        required=False, allow_blank=True, write_only=True,
    )

    class Meta:
        model = Enquiry
        fields = (
            "id", "project", "full_name", "mobile", "email",
            "message", "source", "website",
        )
        read_only_fields = ("id",)
        extra_kwargs = {
            "source": {"required": False},
            "project": {"required": False, "allow_null": True},
        }

    def validate_website(self, value):
        if value:
            raise serializers.ValidationError("Spam detected.")
        return value

    def create(self, validated_data):
        validated_data.pop("website", None)
        return super().create(validated_data)
