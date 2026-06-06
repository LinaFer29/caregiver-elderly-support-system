from rest_framework import serializers
from .models import Caregiver, Elderly, User

class UserRegisterSerializer(serializers.ModelSerializer):
    caregiver_type = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'password',
            'first_name',
            'last_name',
            'role',
            'caregiver_type',
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        caregiver_type = validated_data.pop('caregiver_type')

        user = User.objects.create_user(
            **validated_data,
            #role='caregiver'
        )

        Caregiver.objects.create(user=user, caregiver_type=caregiver_type)

        return user
        
class CaregiverSerializer(serializers.ModelSerializer):
   user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
   class Meta:
        model = Caregiver
        fields = '__all__'

class ElderlySerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(min_value=1, allow_null=True)

    class Meta:
        model = Elderly
        fields = [
            'id',
            'first_name',
            'last_name',
            'age',
            'relationship_to_caregiver',
            'dependency_level',
            'underlying_conditions',
        ]

    def create(self, validated_data):
        request = self.context.get('request')

        caregiver = Caregiver.objects.get(user=request.user)

        return Elderly.objects.create(caregiver=caregiver, **validated_data)

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.age = validated_data.get('age', instance.age)
        instance.relationship_to_caregiver = validated_data.get(
            'relationship_to_caregiver', instance.relationship_to_caregiver
        )
        instance.dependency_level = validated_data.get(
            'dependency_level', instance.dependency_level
        )
        instance.underlying_conditions = validated_data.get(
            'underlying_conditions', instance.underlying_conditions
        )
        instance.save()
        return instance
        
