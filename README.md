# 투표록 7개 선거 빠른 심사 앱

모바일 GitHub 업로드 전용 3파일 버전입니다.

## 업로드 파일

GitHub 저장소에 아래 3개 파일만 올리면 됩니다.

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
- 7개 선거별 숫자 입력
- 잔여매수 자동 계산
- 교부매수 자동 계산
- 투표자수계 검산
- 선거인명부등재자 검산
- 정상 / 재확인 판정
- CSV 다운로드

## 실행 방법

터미널에 붙이세요.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 향후 개선

다음 버전에서 OCR 자동 인식 기능을 추가할 수 있습니다.
