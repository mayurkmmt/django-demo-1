from rest_framework import serializers

from .models import Service
from .models import ServiceTranslation


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'


class ServiceTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceTranslation
        fields = ['language', 'name', 'description', 'url']
