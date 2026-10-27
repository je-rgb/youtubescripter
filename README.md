# 🎬 YouTube Scripter (유튜브 자막/대본 추출기)

유튜브 영상 URL을 입력받아 한국어 및 다국어 자막을 추출하고, 텍스트 파일로 저장할 수 있는 파이썬 & Streamlit 웹 서비스입니다.

---

## ✨ 주요 기능
- **간편한 링크 입력**: 유튜브 전체 URL 또는 11자리 비디오 ID 입력 지원
- **다국어 지원**: 한국어(`ko`), 영어(`en`) 등 우선 언어 선택 및 자동 폴백(fallback) 지원
- **타임스탬프 토글**: 타임스탬프 포함(`[MM:SS] 대사`) 또는 순수 텍스트 대본 모드 선택
- **파일 다운로드**: 추출된 대본을 원클릭으로 `.txt` 파일 다운로드
- **버전 호환성**: `youtube-transcript-api` 최신 버전(1.x) 및 구버전(0.6.x) 완벽 대응

---

## 🚀 빠른 시작

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. Streamlit 웹 앱 실행
```bash
streamlit run app.py
```

### 3. CLI 스크립트 실행 (콘솔 모드)
```bash
python get_transcript.py
```
