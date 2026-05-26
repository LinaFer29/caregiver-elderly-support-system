
from rest_framework import serializers
from activities.models import Activity
from .models import Assignment, Program

class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = '__all__'
        read_only_fields = ['caregiver']

class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = '__all__'

class ActivityWithProgramSerializer(serializers.ModelSerializer):
    program = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = [
            'id',
            'title',
            'description',
            'category',
            'program'
        ]

    def get_program(self, obj):
        program = obj.program_set.first()  # relación inversa

        if not program:
            return None

        return {
            "id": program.id,
            "date": program.date,
            "time": program.time,
            "frequency": program.frequency,
            "is_active": program.is_active
        }


class RoutineCatalogActivitySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_color = serializers.CharField(source="category.color", read_only=True)
    category_icon = serializers.CharField(source="category.icon", read_only=True)

    class Meta:
        model = Activity
        fields = [
            "id",
            "title",
            "description",
            "category",
            "category_name",
            "category_color",
            "category_icon",
        ]


class RoutineCreateSerializer(serializers.Serializer):
    elderly_id = serializers.IntegerField()
    date = serializers.DateField()
    activities = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )

    def validate_activities(self, value):
        validated = []
        for item in value:
            activity_id = item.get("activity_id")
            time = item.get("time")
            frequency = item.get("frequency")
            is_active = item.get("is_active", True)

            if not isinstance(activity_id, int):
                raise serializers.ValidationError("Cada actividad debe incluir activity_id válido.")

            if not time:
                raise serializers.ValidationError("Cada actividad debe incluir hora.")

            if frequency not in ["daily", "weekly"]:
                raise serializers.ValidationError("La frecuencia debe ser daily o weekly.")

            validated.append({
                "activity_id": activity_id,
                "time": time,
                "frequency": frequency,
                "is_active": bool(is_active),
            })

        return validated
