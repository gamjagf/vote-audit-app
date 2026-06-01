# 투표록 7개 선거 OCR 자동심사 앱 v2

OCR 보정 강화 3파일 버전입니다.

## GitHub 업로드 파일

- app.py
- requirements.txt
- README.md

## Streamlit Cloud 설정

- Main file path: app.py

## 기능

- 사진 선택
- 카메라 촬영
- OCR 숫자 자동 인식
- 원본/확대/흑백대비/이진화/선명도 보정 OCR
- OCR 숫자 목록 표시
- 자동 입력 초안 생성
- 7개 선거 자동 검산

## 주의

첫 실행 시 EasyOCR 모델 로딩으로 시간이 걸립니다.
사진이 흐리거나 숫자가 작으면 OCR 숫자 목록이 []로 나올 수 있습니다.
