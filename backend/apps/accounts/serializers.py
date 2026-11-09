from django.contrib.auth import authenticate
# pyrefly: ignore [missing-import]
from rest_framework import serializers
# pyrefly: ignore [missing-import]
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "organization", "designation", "first_name", "last_name"]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs["username"]
        password = attrs["password"]

        user = authenticate(username=identifier, password=password)
        if not user:
            # Check if identifier was passed as email
            try:
                candidate = User.objects.get(email__iexact=identifier)
                if candidate.check_password(password):
                    user = candidate
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                pass

        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled.")
        attrs["user"] = user
        return attrs

    def tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token)}
