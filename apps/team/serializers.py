from rest_framework import serializers

from .models import TeamMember


class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = (
            "id", "slug", "name", "designation", "bio",
            "photo", "linkedin_url", "display_order",
        )
