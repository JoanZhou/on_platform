from rest_framework import serializers
from django.contrib.auth.models import User

from on.models import RunningGoal, RunningPunchRecord, Activity
from on.user import UserInfo


class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInfo
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    profile = UserInfoSerializer(many=False, read_only=True)
    class Meta:
        model = User
        fields = '__all__'


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = '__all__'


class RunningTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunningGoal
        fields = '__all__'


class RunningTaskRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunningPunchRecord
        fields = '__all__'
