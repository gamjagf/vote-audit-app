# 투표록 7개 선거 OCR 자동심사 앱

모바일 GitHub 업로드 전용 3파일 OCR 버전입니다.

## GitHub 업로드 파일

- app.py
- requirements.txt
- README.md

## Streamlit Cloud 설정

- Repository: gamjagf/vote-audit-app
- Branch: main
- Main file path: app.py

## 기능

- 사진 선택
- 카메라 촬영
- EasyOCR 숫자 자동 인식
- OCR 숫자 목록 표시
- 자동 입력 초안 생성
- 사용자가 숫자 확인 및 수정
- 7개 선거 자동 검산
- 정상 / 재확인 판정
- CSV 다운로드

## 주의

첫 실행 시 EasyOCR 모델 다운로드 때문에 시간이 걸릴 수 있습니다.
사진이 흐리거나 그림자가 있으면 OCR 정확도가 낮아질 수 있습니다.
