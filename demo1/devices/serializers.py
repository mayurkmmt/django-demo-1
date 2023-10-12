from rest_framework import serializers

from .models import Device
from .models import Brand
from .models import ProductFamily
from .models import DeviceService


class DeviceServiceSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    category = serializers.CharField(source='service.category')
    slug = serializers.CharField(source='service.slug')
    currency = serializers.CharField(source='get_currency_display')
    icon = serializers.FileField(source='service.icon')

    def get_name(self, obj):
        return obj.service.get_name()

    def get_description(self, obj):
        return obj.service.get_description()

    def get_url(self, obj):
        return obj.service.get_url()

    class Meta:
        model = DeviceService
        exclude = ['device']


class TerseBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['slug', 'name']


class DeviceSerializer(serializers.ModelSerializer):
    services = DeviceServiceSerializer(many=True, read_only=True)
    brand = TerseBrandSerializer(read_only=True, source='product_family.brand')
    icon = serializers.SerializerMethodField()

    def get_icon(self, obj):
        icon = obj.icon if obj.icon else obj.product_family.icon
        if icon:
            return self.context['request'].build_absolute_uri(icon.url)
        return None

    class Meta:
        model = Device
        fields = '__all__'


class TerseDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['name', 'slug']


class ProductFamilySerializer(serializers.ModelSerializer):
    devices = DeviceSerializer(many=True)

    class Meta:
        model = ProductFamily
        fields = '__all__'


class BrandSerializer(serializers.ModelSerializer):
    product_families = ProductFamilySerializer(many=True)

    class Meta:
        model = Brand
        fields = '__all__'
