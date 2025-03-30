import os
import sys

# 프로젝트 루트 설정
base_dir = os.path.dirname(os.path.abspath(__file__))

# Python 경로 설정
sys.path.insert(0, base_dir)

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_cheatkey.blog_cheatkey.backend.blog_cheatkey.settings')

# WSGI 애플리케이션 가져오기
try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception as e:
    error_msg = str(e)
    
    # 오류 발생 시 간단한 응답 반환
    def application(environ, start_response):
        status = '200 OK'
        headers = [('Content-type', 'text/html; charset=utf-8')]
        start_response(status, headers)
        html = """
        <html>
        <head>
            <title>블로그 치트키</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                .container { max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #0066cc; }
                .message { padding: 15px; background-color: #f8f9fa; border-left: 5px solid #0066cc; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>블로그 치트키</h1>
                <div class="message">
                    <p>사이트가 현재 점검 중입니다. 잠시 후 다시 방문해 주세요.</p>
                    <p>The site is currently undergoing maintenance. Please check back later.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return [html.encode('utf-8')]