from django.conf import settings
from rest_framework import serializers

from .models import TrainerCertificate, TrainerProfile

# Configurable defaults (override in settings if you want)
DEFAULT_MAX_CERT_SIZE = getattr(settings, "MAX_CERT_FILE_SIZE", 10 * 1024 * 1024)
DEFAULT_ALLOWED_CERT_CONTENT_TYPES = getattr(
    settings,
    "ALLOWED_CERT_CONTENT_TYPES",
    {"application/pdf", "image/jpeg", "image/png"},
)


class TrainerProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)

    # return certificates via a SerializerMethodField so we don't rely on related_name
    certificates = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TrainerProfile
        fields = [
            "id",
            "user_id",
            "bio",
            "specialties",
            "experience_years",
            "is_completed",
            "created_at",
            "certificates",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "created_at",
            "is_completed",
            "certificates",
        ]

    def get_certificates(self, obj):
        # query certs linked to this profile, newest first
        qs = obj.certificates.all().order_by("-uploaded_at")
        return TrainerCertificateModelSerializer(
            qs, many=True, context=self.context
        ).data

    def validate_experience_years(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("experience_years must be >= 0")
        return value


class TrainerCertificateModelSerializer(serializers.ModelSerializer):
    filename = serializers.CharField(source="file.name", read_only=True)
    file_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TrainerCertificate
        # return id, filename, file_url, uploaded_at
        fields = ["id", "filename", "file_url", "uploaded_at"]
        read_only_fields = ["id", "filename", "file_url", "uploaded_at"]

    def get_file_url(self, instance):
        request = self.context.get("request")
        if instance.file:
            try:
                url = instance.file.url
            except ValueError:
                return None
            if request:
                return request.build_absolute_uri(url)
            return url
        return None


class CertificateUploadSerializer(serializers.Serializer):
    # Accept either a single file under 'file' or multiple under 'files'
    file = serializers.FileField(required=False, write_only=True)
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True,
        allow_empty=False,
    )

    def validate(self, attrs):
        single = attrs.get("file")
        many = attrs.get("files")
        if not single and not many:
            raise serializers.ValidationError("Provide either 'file' or 'files'.")

        if single and not many:
            attrs["files"] = [single]

        # now attrs["files"] exists and is a list
        validated_files = []
        max_size = getattr(self, "max_size", DEFAULT_MAX_CERT_SIZE)
        allowed = getattr(self, "allowed_types", DEFAULT_ALLOWED_CERT_CONTENT_TYPES)

        for f in attrs["files"]:
            if f.size > max_size:
                raise serializers.ValidationError(
                    {"files": f"{f.name}: file too large (max {max_size} bytes)."}
                )
            content_type = getattr(f, "content_type", None)
            if content_type not in allowed:
                raise serializers.ValidationError(
                    {"files": f"{f.name}: unsupported file type ({content_type})."}
                )
            validated_files.append(f)

        attrs["files"] = validated_files
        return attrs
