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
    # USER FIELDS
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    username = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Elderly
        fields = [
            'id',

            # USER
            'first_name',
            'last_name',
            'username',
            'email',
            'password',

            # ELDERLY
            'relationship_to_caregiver',
            'dependency_level',
            'underlying_conditions',
        ]

    def create(self, validated_data):
        request = self.context.get('request')

        # USER DATA
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        username = validated_data.pop('username')
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        # CREATE USER
        user = User.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            password=password,
            role='elderly'
        )

        caregiver = Caregiver.objects.get(user=request.user)

        elderly = Elderly.objects.create(
            user=user,
            caregiver=caregiver,
            **validated_data
        )

        return elderly

    def update(self, instance, validated_data):
        user = instance.user

        # UPDATE USER
        user.first_name = validated_data.pop('first_name', user.first_name)
        user.last_name = validated_data.pop('last_name', user.last_name)
        user.username = validated_data.pop('username', user.username)
        user.email = validated_data.pop('email', user.email)

        password = validated_data.pop('password', None)

        if password:
            user.set_password(password)

        user.save()

        # UPDATE ELDERLY
        instance.relationship_to_caregiver = validated_data.get(
            'relationship_to_caregiver',
            instance.relationship_to_caregiver
        )

        instance.dependency_level = validated_data.get(
            'dependency_level',
            instance.dependency_level
        )

        instance.underlying_conditions = validated_data.get(
            'underlying_conditions',
            instance.underlying_conditions
        )

        instance.save()

        return instance

    def to_representation(self, instance):
        return {
            "id": instance.id,

            # USER
            "first_name": instance.user.first_name,
            "last_name": instance.user.last_name,
            "username": instance.user.username,
            "email": instance.user.email,

            # ELDERLY
            "relationship_to_caregiver": instance.relationship_to_caregiver,
            "dependency_level": instance.dependency_level,
            "underlying_conditions": instance.underlying_conditions,
        }
        
