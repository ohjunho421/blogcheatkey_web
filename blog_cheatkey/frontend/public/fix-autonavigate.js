/**
 * BlogCheatKey 자동 페이지 이동 수정 스크립트
 * 로딩바 100% 완료 후 자동 이동 오류(broken pipe) 해결을 위한 패치
 */
(function() {
  // 로딩바 진행률 모니터링 함수
  function watchLoadingProgress() {
    // 로딩바 요소 확인 (진행률 100% 감지용)
    const progressCheck = setInterval(function() {
      const progressBar = document.querySelector('.progress-bar');
      const progressText = document.querySelector('.progress-text');
      
      if (progressBar && progressText) {
        const progress = parseInt(progressText.innerText);
        console.log('현재 진행률:', progress);
        
        // 완료된 경우 (100%)
        if (progress === 100) {
          console.log('로딩 100% 완료 - 페이지 이동 준비');
          
          // 진행 완료 메시지 표시
          const messageEl = document.querySelector('.generation-message');
          if (messageEl) {
            messageEl.innerText = '콘텐츠 생성이 완료되었습니다. 곧 자동으로 이동합니다...';
          }
          
          // 페이지 이동 준비
          setTimeout(function() {
            // 콘텐츠 ID 추출 (URL 또는 DOM에서)
            const contentIdMatch = document.body.innerHTML.match(/content\/([a-zA-Z0-9-]+)/);
            if (contentIdMatch && contentIdMatch[1]) {
              const contentId = contentIdMatch[1];
              console.log('콘텐츠 ID 발견:', contentId);
              
              // 페이지 이동 실행 (네트워크 연결 끊김)
              window.location.href = `/content/${contentId}`;
            }
          }, 2000); // 2초 후 이동
          
          // 인터벌 정리
          clearInterval(progressCheck);
        }
      }
    }, 1000); // 1초마다 확인
  }
  
  // 페이지 로드 완료 시 실행
  window.addEventListener('load', function() {
    console.log('페이지 로드 완료 - 자동 이동 감시 시작');
    watchLoadingProgress();
  });
})();
