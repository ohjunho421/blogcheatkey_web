import os
import sys

def main():
    # 경로에 backend 디렉토리 추가
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
    
    # 설정 모듈 경로 변경
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.blog_cheatkey.settings')
    # 또는 
    # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.blog_cheatkey.settings')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()