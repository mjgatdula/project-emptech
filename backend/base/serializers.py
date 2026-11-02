import io
import uuid
from datetime import timedelta
from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework import serializers
from .models import ITEM_REPORT, SITE, CATEGORY, OWNERSHIP_CLAIM
from .permissions import can_manage
from .services import editable


class ReportWriteSerializer(serializers.ModelSerializer):
    site = serializers.PrimaryKeyRelatedField(queryset=SITE.objects.filter(is_active=True))
    category = serializers.PrimaryKeyRelatedField(queryset=CATEGORY.objects.filter(is_active=True))
    validity_days = serializers.ChoiceField(choices=[7, 14, 30], default=30, write_only=True)
    remove_image = serializers.BooleanField(default=False, write_only=True)

    class Meta:
        model = ITEM_REPORT
        fields = ['report_type', 'title', 'description', 'site', 'category', 'location', 'item_date', 'time', 'image', 'validity_days', 'remove_image']
        extra_kwargs = {'title': {'min_length': 3}, 'description': {'min_length': 10, 'max_length': 4000}, 'location': {'min_length': 3}, 'image': {'required': False, 'allow_null': True}, 'time': {'required': False, 'allow_null': True}}

    def validate(self, attrs):
        if attrs.get('remove_image') and attrs.get('image'):
            raise serializers.ValidationError('Choose either a replacement photograph or removal of the current photograph.')
        return attrs

    def validate_item_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('The incident date cannot be in the future.')
        return value

    def validate_image(self, upload):
        if upload is None:
            return ''
        if upload.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Images must be 5 MB or smaller.')
        try:
            image = Image.open(upload)
            if image.format not in {'JPEG', 'PNG', 'WEBP'} or image.width * image.height > 20_000_000:
                raise ValueError('Unsupported image')
            image.load()
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((2400, 2400))
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=88)
            return ContentFile(output.getvalue(), name=f'{uuid.uuid4().hex}.jpg')
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise serializers.ValidationError('Choose a valid JPEG, PNG or WebP image with at most 20 megapixels.')

    def create(self, validated_data):
        days = validated_data.pop('validity_days', 30)
        validated_data.pop('remove_image', False)
        instance = ITEM_REPORT(reference_number=f'TIP-{timezone.localdate():%Y%m%d}-{uuid.uuid4().hex[:12].upper()}', expires_at=timezone.now() + timedelta(days=days), **validated_data)
        if instance.image:
            self.context['uploads'].append(instance.image)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        days = validated_data.pop('validity_days', None)
        remove = validated_data.pop('remove_image', False)
        if days is not None:
            instance.expires_at = timezone.now() + timedelta(days=days)
        if remove:
            instance.image = ''
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if validated_data.get('image'):
            self.context['uploads'].append(instance.image)
        instance.save()
        return instance


class ReportSerializer(serializers.ModelSerializer):
    reference = serializers.CharField(source='reference_number')
    status = serializers.SerializerMethodField()
    date = serializers.DateField(source='item_date')
    expiresAt = serializers.DateTimeField(source='expires_at')
    createdAt = serializers.DateTimeField(source='created_at')
    siteName = serializers.CharField(source='site.name')
    categoryName = serializers.CharField(source='category.name')
    reviewStatus = serializers.CharField(source='moderation_status')
    closed = serializers.BooleanField(source='is_closed')
    inCustody = serializers.BooleanField(source='has_custody')
    released = serializers.BooleanField(source='is_released')
    image = serializers.SerializerMethodField()
    isOwner = serializers.SerializerMethodField()
    canEdit = serializers.SerializerMethodField()
    canManage = serializers.SerializerMethodField()
    canDelete = serializers.SerializerMethodField()

    class Meta:
        model = ITEM_REPORT
        fields = ['id', 'reference', 'report_type', 'status', 'title', 'description', 'location', 'date', 'time', 'site', 'siteName', 'category', 'categoryName', 'expiresAt', 'createdAt', 'reviewStatus', 'closed', 'inCustody', 'released', 'image', 'photo_visibility_status', 'isOwner', 'canEdit', 'canManage', 'canDelete']

    def get_status(self, report):
        return report.get_report_type_display()

    def get_isOwner(self, report):
        return self.context['request'].user.pk == report.reporter_id

    def get_canManage(self, report):
        return can_manage(self.context['request'].user, report)

    def get_canEdit(self, report):
        return self.get_isOwner(report) and editable(report)

    def get_canDelete(self, report):
        return self.get_isOwner(report) and editable(report) and not report.moderation_decisions.exists()

    def get_image(self, report):
        if report.image and (report.photo_visibility_status == 'approved' or self.get_isOwner(report) or self.get_canManage(report)):
            return f'/reports/{report.pk}/image/'
        return None


class ClaimWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OWNERSHIP_CLAIM
        fields = ['private_explanation']
        extra_kwargs = {'private_explanation': {'min_length': 15, 'max_length': 4000}}
