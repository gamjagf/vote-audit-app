# 투표록 7개 선거 OCR 자동심사 앱 - 가벼운 OCR API 버전

EasyOCR를 제거하고 OCR.Space API를 사용하는 3파일 버전입니다.

## GitHub 업로드 파일

- app.py
- requirements.txt
- README.md

## Streamlit Cloud 설정

- Main file path: app.py
- Python version: 3.11 권장

## 기능

- 사진 선택
- 카메라 촬영
- OCR API 숫자 자동 인식
- OCR 숫자 목록 표시
- 자동 입력 초안 생성
- 7개 선거 자동 검산

## 주의

이 버전은 외부 OCR API를 사용합니다.
실제 업무용 문서 사용 시 보안 기준을 확인해야 합니다.

OCR.Space API 키를 발급받은 경우 Streamlit Secrets에 아래처럼 등록할 수 있습니다.

OCR_SPACE_API_KEY = "발급받은_API_KEY"
