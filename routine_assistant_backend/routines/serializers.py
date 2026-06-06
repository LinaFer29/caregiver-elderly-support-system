
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
        queryset = obj.program_set.all()
        elderly_id = self.context.get("elderly_id")
        caregiver = self.context.get("caregiver")

        if elderly_id is not None:
            queryset = queryset.filter(elderly_id=elderly_id)
        elif caregiver is not None:
            queryset = queryset.filter(caregiver=caregiver)

        program = queryset.order_by("date", "time").first()

        if not program:
            return None

        return {
            "id": program.id,
            "elderly": program.elderly_id,
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
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    activities = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )

    def validate(self, attrs):
        start_date = attrs["start_date"]
        end_date = attrs.get("end_date")
        activities = attrs.get("activities", [])

        has_recurring_activity = any(
            item.get("frequency") in ["daily", "weekly", "monthly"]
            for item in activities
        )

        if has_recurring_activity and end_date is None:
            raise serializers.ValidationError({
                "end_date": "La fecha fin es obligatoria para frecuencias recurrentes."
            })

        if has_recurring_activity and end_date is not None and end_date <= start_date:
            raise serializers.ValidationError({
                "end_date": "Las actividades recurrentes requieren una fecha fin posterior a la fecha de inicio."
            })

        if not has_recurring_activity:
            attrs["end_date"] = start_date
        elif end_date is not None and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "La fecha fin no puede ser menor que la fecha inicio."
            })

        return attrs

    def validate_activities(self, value):
        validated = []
        for item in value:
            activity_id = item.get("activity_id")
            time = item.get("time")
            frequency = item.get("frequency")
            is_active = item.get("is_active", True)
            additional_instructions = item.get("additional_instructions", "")

            if not isinstance(activity_id, int):
                raise serializers.ValidationError("Cada actividad debe incluir activity_id válido.")

            if not time:
                raise serializers.ValidationError("Cada actividad debe incluir hora.")

            if frequency not in ["once", "daily", "weekly", "monthly"]:
                raise serializers.ValidationError("La frecuencia debe ser once, daily, weekly o monthly.")

            if additional_instructions is not None and not isinstance(additional_instructions, str):
                raise serializers.ValidationError("Las instrucciones adicionales deben ser texto.")

            validated.append({
                "activity_id": activity_id,
                "time": time,
                "frequency": frequency,
                "is_active": bool(is_active),
                "additional_instructions": additional_instructions,
            })

        return validated
