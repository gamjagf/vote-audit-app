
import streamlit as st
from PIL import Image
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="투표록 7개 선거 빠른 심사 앱", page_icon="🗳️", layout="wide")

st.title("🗳️ 투표록 7개 선거 빠른 심사 앱")
st.caption("카메라 촬영 또는 이미지 업로드 후, 선거별 수령·잔여·교부·투표자수 항목을 빠르게 검산합니다.")

ELECTIONS = [
    "교육감 선거",
    "도지사 선거",
    "시장·군수·구청장 선거",
    "지역구 도의원 선거",
    "비례대표 도의원 선거",
    "지역구 시·군의원 선거",
    "비례대표 시·군의원 선거",
]

st.info(
    "현재 버전은 현장 심사용 MVP입니다. 사진을 올린 뒤 숫자를 확인·수정하면 즉시 검산합니다. "
    "OCR은 환경에 따라 정확도가 달라서, 최종 제출 전에는 원본 투표록과 대조해 주세요."
)

with st.sidebar:
    st.header("📷 이미지 입력")
    input_method = st.radio("입력 방식", ["파일 업로드", "카메라 촬영"], horizontal=False)
    if input_method == "파일 업로드":
        img_file = st.file_uploader("투표록 사진 업로드", type=["jpg", "jpeg", "png"])
    else:
        img_file = st.camera_input("투표록 촬영")

    st.divider()
    st.header("⚙️ 심사 기준")
    st.write("① 잔여매수 = 끝번호 - 시작번호 + 1 + 오·훼손")
    st.write("② 교부매수 = 수령매수 - 잔여매수")
    st.write("③ 투표자수계 = 교부매수")
    st.write("④ 선거인명부등재자 = 투표자수계 - 특수유형 합계")

if img_file:
    image = Image.open(img_file)
    st.subheader("📌 업로드된 투표록 이미지")
    st.image(image, use_container_width=True)

st.subheader("🧾 1. 선거별 숫자 입력 또는 확인")

default_rows = []
for name in ELECTIONS:
    default_rows.append({
        "선거명": name,
        "수령매수": 0,
        "잔여_시작번호": 0,
        "잔여_끝번호": 0,
        "오훼손_미교부": 0,
        "잔여매수_기재값": 0,
        "교부매수_기재값": 0,
        "투표자수계_기재값": 0,
        "거소미발송반송": 0,
        "결정서지참": 0,
        "거소투표용지회송봉투반납": 0,
        "귀국투표자": 0,
        "선거인명부등재자_기재값": 0,
    })

df = pd.DataFrame(default_rows)

edited = st.data_editor(
    df,
    use_container_width=True,
    num_rows="fixed",
    hide_index=True,
    column_config={
        "선거명": st.column_config.TextColumn("선거명", disabled=True),
        "수령매수": st.column_config.NumberColumn("수령매수", min_value=0, step=1),
        "잔여_시작번호": st.column_config.NumberColumn("잔여 시작번호", min_value=0, step=1),
        "잔여_끝번호": st.column_config.NumberColumn("잔여 끝번호", min_value=0, step=1),
        "오훼손_미교부": st.column_config.NumberColumn("오·훼손 미교부", min_value=0, step=1),
        "잔여매수_기재값": st.column_config.NumberColumn("잔여매수 기재값", min_value=0, step=1),
        "교부매수_기재값": st.column_config.NumberColumn("교부매수 기재값", min_value=0, step=1),
        "투표자수계_기재값": st.column_config.NumberColumn("투표자수계 기재값", min_value=0, step=1),
        "거소미발송반송": st.column_config.NumberColumn("거소 미발송·반송", min_value=0, step=1),
        "결정서지참": st.column_config.NumberColumn("결정서 지참", min_value=0, step=1),
        "거소투표용지회송봉투반납": st.column_config.NumberColumn("거소투표용지·회송봉투 반납", min_value=0, step=1),
        "귀국투표자": st.column_config.NumberColumn("귀국투표자", min_value=0, step=1),
        "선거인명부등재자_기재값": st.column_config.NumberColumn("선거인명부등재자 기재값", min_value=0, step=1),
    }
)

st.subheader("✅ 2. 자동 심사 결과")

result_rows = []

for _, r in edited.iterrows():
    start = int(r["잔여_시작번호"])
    end = int(r["잔여_끝번호"])
    damaged = int(r["오훼손_미교부"])
    received = int(r["수령매수"])

    if start > 0 and end >= start:
        calc_left = end - start + 1 + damaged
    else:
        calc_left = 0

    written_left = int(r["잔여매수_기재값"])
    written_issued = int(r["교부매수_기재값"])
    written_voters_total = int(r["투표자수계_기재값"])
    special = (
        int(r["거소미발송반송"])
        + int(r["결정서지참"])
        + int(r["거소투표용지회송봉투반납"])
        + int(r["귀국투표자"])
    )
    written_registry = int(r["선거인명부등재자_기재값"])

    calc_issued = received - calc_left if received >= calc_left else -1
    calc_registry = written_voters_total - special

    check_left = (calc_left == written_left)
    check_issued = (calc_issued == written_issued)
    check_voters = (written_voters_total == written_issued)
    check_registry = (calc_registry == written_registry)

    all_ok = check_left and check_issued and check_voters and check_registry

    if all_ok:
        status = "정상"
        memo = "이상 없음"
    else:
        status = "재확인"
        problems = []
        if not check_left:
            problems.append(f"잔여매수 불일치: 계산 {calc_left}, 기재 {written_left}")
        if not check_issued:
            problems.append(f"교부매수 불일치: 계산 {calc_issued}, 기재 {written_issued}")
        if not check_voters:
            problems.append(f"투표자수계 불일치: 투표자수계 {written_voters_total}, 교부매수 {written_issued}")
        if not check_registry:
            problems.append(f"선거인명부등재자 불일치: 계산 {calc_registry}, 기재 {written_registry}")
        memo = " / ".join(problems)

    result_rows.append({
        "선거명": r["선거명"],
        "잔여매수_계산값": calc_left,
        "교부매수_계산값": calc_issued,
        "특수유형합계": special,
        "선거인명부등재자_계산값": calc_registry,
        "잔여검산": "OK" if check_left else "오류",
        "교부검산": "OK" if check_issued else "오류",
        "투표자수검산": "OK" if check_voters else "오류",
        "명부등재자검산": "OK" if check_registry else "오류",
        "최종판정": status,
        "비고": memo,
    })

result_df = pd.DataFrame(result_rows)

ok_count = (result_df["최종판정"] == "정상").sum()
bad_count = (result_df["최종판정"] == "재확인").sum()

col1, col2, col3 = st.columns(3)
col1.metric("전체 선거 수", len(result_df))
col2.metric("정상", int(ok_count))
col3.metric("재확인 필요", int(bad_count))

st.dataframe(result_df, use_container_width=True, hide_index=True)

if bad_count == 0:
    st.success("7개 선거 모두 검산 결과 정상입니다.")
else:
    st.error("재확인 필요한 선거가 있습니다. 비고란의 불일치 항목을 원본과 대조해 주세요.")

st.subheader("📄 3. 심사 결과 저장")

csv = result_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="심사결과 CSV 다운로드",
    data=csv,
    file_name="투표록_심사결과.csv",
    mime="text/csv"
)

st.caption("※ 본 앱은 심사 보조용입니다. 공식 판단은 선거관리 절차와 원본 서류 확인에 따르십시오.")
