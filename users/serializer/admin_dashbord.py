from rest_framework import serializers
from users.models import Product, ProductPrice, RecommendedQuantity
from report.models import HarvestReport, LivestockProduction
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class ProductPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPrice
        fields = '__all__'

class RecommendedQuantitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendedQuantity
        fields = '__all__'

class HarvestReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = HarvestReport
        fields = '__all__'

class LivestockProductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LivestockProduction
        fields = '__all__'
