from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from .serializers import UserSerializer
from allauth.socialaccount.models import SocialToken, SocialAccount
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
import jwt
from django.conf import settings
from django.shortcuts import redirect

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Simply delete the token to logout
        request.user.auth_token.delete()
        return Response({"detail": "로그아웃이 성공적으로 처리되었습니다."}, status=status.HTTP_200_OK)

class ProfileView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_object(self):
        return self.request.user

class ProfileUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_object(self):
        return self.request.user
    
class SocialLoginView(APIView):
    """
    소셜 로그인 후 DRF 토큰을 반환하는 뷰
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        provider = request.data.get('provider')
        access_token = request.data.get('access_token')
        
        if not provider or not access_token:
            return Response(
                {"error": "Provider와 access_token이 필요합니다."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # allauth를 통해 등록된 소셜 계정 조회
            social_account = SocialAccount.objects.get(provider=provider, uid=request.data.get('uid'))
            user = social_account.user
            
            # DRF 토큰 생성 또는 조회
            token, created = Token.objects.get_or_create(user=user)
            
            # 사용자 정보와 토큰 반환
            return Response({
                'token': token.key,
                'user': UserSerializer(user).data
            })
        except SocialAccount.DoesNotExist:
            return Response(
                {"error": "해당 소셜 계정을 찾을 수 없습니다."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SocialLoginCallbackView(APIView):
    """
    소셜 로그인 콜백을 처리하고 프론트엔드로 리디렉션하는 뷰
    """
    permission_classes = [AllowAny]
    
    def get(self, request, provider):
        code = request.GET.get('code')
        # 프론트엔드 URL로 리디렉션 (React 앱)
        # 매개변수로 인증 코드와 공급자 정보 전달
        try:
            redirect_uri = f"{settings.FRONTEND_URL}/auth/callback?code={code}&provider={provider}"
            return redirect(redirect_uri)
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )