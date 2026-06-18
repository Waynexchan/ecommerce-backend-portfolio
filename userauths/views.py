from django.shortcuts import render

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.encoding import force_bytes, force_str
from rest_framework.parsers import MultiPartParser, FormParser
from userauths.models import User,Profile
from userauths.serializer import MyTokenObtainPairSerializer, ProfileSerializer, RegisterSerializer, UserSerializer

import random
import shortuuid
# Create your views here.

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny, )
    serializer_class = RegisterSerializer

def generate_otp():
    uuid_key = shortuuid.uuid()
    unique_key = uuid_key[:6]
    return unique_key

class PasswordResetEmailVerify(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

    def get_object(self):
        email = self.kwargs['email']
        try:
            user = User.objects.get(email=email)
            if user:
                user.otp = generate_otp()
                user.save()

                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                otp = user.otp

                link = f"{settings.SITE_URL}/create-new-password?otp={otp}&uidb64={uidb64}"
                merge_data = {'link': link, 'username': user.username}

                subject = "Password Reset Request"
                text_body = render_to_string("email/password_reset.txt", merge_data)
                html_body = render_to_string("email/password_reset.html", merge_data)

                msg = EmailMultiAlternatives(
                    subject=subject, from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email], body=text_body
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send()

                return user
        except User.DoesNotExist:
            return None

class PasswordChangeView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        payload = request.data

        otp = payload['otp']
        uidb64 = payload['uidb64']
        password = payload['password']

        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=user_id, otp=otp)
            if user:
                user.set_password(password)
                user.otp = ""
                user.save()

                return Response({"message": "Password Changed Successfully"}, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            return Response({"message": "An Error Occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        user_id = self.kwargs['user_id']
        user = User.objects.get(id=user_id)
        profile = Profile.objects.get(user=user)
        return profile