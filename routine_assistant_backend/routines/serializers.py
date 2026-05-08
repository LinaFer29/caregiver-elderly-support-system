
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