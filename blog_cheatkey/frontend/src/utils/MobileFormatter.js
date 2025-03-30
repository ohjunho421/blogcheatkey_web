// MobileFormatter.js
// 모바일 화면에 최적화된 줄바꿈 포맷팅을 위한 유틸리티 클래스

class MobileFormatter {
    /**
     * 모바일 화면에 최적화된 포맷으로 콘텐츠 변환
     * 한글 기준 적절한 위치에서 자연스럽게 줄바꿈 처리
     * 
     * @param {string} content - 변환할 원본 콘텐츠
     * @returns {string} - 모바일 최적화된 콘텐츠
     */
    static formatForMobile(content) {
      if (!content) return '';
      
      // 줄 단위로 분리
      const lines = content.split('\n');
      const formattedLines = [];
      
      for (let line of lines) {
        // 마크다운 제목은 그대로 유지
        if (line.trim().startsWith('#')) {
          formattedLines.push(line);
          continue;
        }
        
        // 빈 줄은 그대로 유지
        if (!line.trim()) {
          formattedLines.push(line);
          continue;
        }
        
        // 목록(리스트) 항목은 그대로 유지
        if (line.trim().match(/^(-|\*|\d+\.)\s/)) {
          formattedLines.push(line);
          continue;
        }
        
        // 코드 블록이나 특수 마크다운 블록은 유지
        if (line.trim().startsWith('```') || line.trim().startsWith('---') || line.trim().startsWith('|')) {
          formattedLines.push(line);
          continue;
        }
        
        // 일반 텍스트는 자연스러운 위치에서 줄바꿈
        this._addFormattedText(line, formattedLines);
      }
      
      return formattedLines.join('\n');
    }
    
    /**
     * 텍스트를 자연스러운 위치에서 줄바꿈하여 추가
     * 
     * @param {string} text - 줄바꿈할 텍스트
     * @param {Array} linesArray - 결과를 저장할 배열
     * @private
     */
    static _addFormattedText(text, linesArray) {
      if (!text.trim()) {
        linesArray.push(text);
        return;
      }
      
      // 정규식을 사용하여 텍스트 분석
      const chunks = [];
      let currentChunk = '';
      let charCount = 0;
      const TARGET_LENGTH = 20; // 목표 길이 (한글이 공백 없이 약 이 정도가 가독성 좋음)
      
      // 단어 단위로 분리
      const words = text.split(' ');
      
      for (let i = 0; i < words.length; i++) {
        const word = words[i];
        
        // 단어 자체가 매우 긴 경우
        if (word.length > TARGET_LENGTH * 1.5) {
          // 현재 청크가 있으면 저장
          if (currentChunk) {
            chunks.push(currentChunk);
            currentChunk = '';
            charCount = 0;
          }
          
          // 긴 단어를 적절히 분할
          let remainingWord = word;
          while (remainingWord.length > TARGET_LENGTH) {
            chunks.push(remainingWord.substring(0, TARGET_LENGTH));
            remainingWord = remainingWord.substring(TARGET_LENGTH);
          }
          
          if (remainingWord) {
            currentChunk = remainingWord;
            charCount = remainingWord.length;
          }
          continue;
        }
        
        // 단어 추가 시 길이 체크
        const wordLength = word.length;
        const newLength = charCount + (currentChunk ? 1 : 0) + wordLength;
        
        // 줄바꿈 결정 로직:
        // 1. 길이가 목표치를 넘을 경우
        // 2. 자연스러운 구분점(콤마, 마침표 등) 뒤에서 줄바꿈
        const shouldBreak = newLength > TARGET_LENGTH || 
                            (newLength > TARGET_LENGTH * 0.7 && 
                             currentChunk.endsWith(',') || 
                             currentChunk.endsWith('.') || 
                             currentChunk.endsWith('?') || 
                             currentChunk.endsWith('!') ||
                             currentChunk.endsWith(':') ||
                             currentChunk.endsWith(';'));
        
        if (shouldBreak && currentChunk) {
          chunks.push(currentChunk);
          currentChunk = word;
          charCount = wordLength;
        } else {
          if (currentChunk) {
            currentChunk += ' ' + word;
            charCount = newLength;
          } else {
            currentChunk = word;
            charCount = wordLength;
          }
        }
      }
      
      // 마지막 청크 저장
      if (currentChunk) {
        chunks.push(currentChunk);
      }
      
      // 모든 청크를 결과 배열에 추가
      linesArray.push(...chunks);
    }
    
    /**
     * HTML 콘텐츠에 모바일 최적화 포맷 적용
     * dangerouslySetInnerHTML과 함께 사용할 수 있는 형태로 변환
     * 
     * @param {string} htmlContent - HTML 형식의 콘텐츠
     * @returns {string} - 모바일 최적화된 HTML 콘텐츠
     */
    static formatHtmlForMobile(htmlContent) {
      if (!htmlContent) return '';
      
      // <br> 태그를 줄바꿈 문자로 변환
      let textContent = htmlContent.replace(/<br\s*\/?>/gi, '\n');
      
      // HTML 태그 제거 (임시 DOM 요소 사용)
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = textContent;
      textContent = tempDiv.textContent || tempDiv.innerText || '';
      
      // 모바일 최적화 포맷 적용
      const formattedText = this.formatForMobile(textContent);
      
      // 줄바꿈을 <br> 태그로 변환
      return formattedText.replace(/\n/g, '<br>');
    }
  }
  
  export default MobileFormatter;