"""Serializers for licensing objects."""
from rest_framework import serializers

from .models import SeatBucket, CompanyLicense


class SeatBucketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeatBucket
        fields = "__all__"


class CompanyLicenseSerializer(serializers.ModelSerializer):
    seat_bucket = SeatBucketSerializer(read_only=True)
    seat_bucket_id = serializers.PrimaryKeyRelatedField(
        queryset=SeatBucket.objects.all(),
        source="seat_bucket",
        write_only=True,
        required=True,
    )

    class Meta:
        model = CompanyLicense
        fields = "__all__"

