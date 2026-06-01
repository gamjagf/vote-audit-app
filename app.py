
import streamlit as st
import pandas as pd
from PIL import Image

st.set_page_config(
    page_title="투표록 7개 선거 빠른 심사 앱",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------
# 기본 스타일
# -----------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
}
.main-title {
    font-size: 2.15rem;
    font-weight: 900;
    line-height: 1.25;
    color: #252936;
}
.sub-text {
    font-size: 1.05rem;
    color: #666;
    line-height: 1.7;
}
.notice {
    background: #eaf4ff;
    color: #075985;
    padding: 1rem;
    border-radius: 1rem;
    font-size: 1.02rem;
    line-height: 1.7;
    margin-top: 1rem;
}
.step-title {
    font-size: 1.4rem;
    font-weight: 850;
    margin-top: 1.8rem;
    margin-bottom: .6rem;
}
.ok-box {
    background: #eaf8ef;
    border-left: 7px solid #22a35a;
    padding: 1rem;
    border-radius: 1rem;
    font-size: 1.05rem;
}
.bad-box {
    background: #fff0f0;
    border-left: 7px solid #e5484d;
    padding: 1rem;
    border-radius: 1rem;
    font-size: 1.05rem;
}
.small-guide {
    background: #f7f7f8;
    padding: 1rem;
    border-radius: 1rem;
    line-height: 1.8;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 계산 함수
# -----------------------------
def to_int(value):
    try:
        if pd.isna(value):
            return 0
        return int(str(value).replace(",", "").strip())
    except Exception:
        return 0

def make_default_table():
    elections = [
        "교육감 선거",
        "도지사 선거",
        "시장·군수·구청장 선거",
        "지역구 도의원 선거",
        "비례대표 도의원 선거",
        "지역구 시·군의원 선거",
        "비례대표 시·군의원 선거",
    ]

    rows = []
    for name in elections:
        rows.append({
            "선거명": name,
            "수령매수": 0,
            "잔여 시작번호": 0,
            "잔여 끝번호": 0,
            "오·훼손 미교부": 0,
            "잔여매수 기재값": 0,
            "교부매수 기재값": 0,
            "투표자수계 기재값": 0,
            "거소 미발송·반송": 0,
            "결정서 지참": 0,
            "거소투표용지·회송봉투 반납": 0,
            "귀국투표자": 0,
            "선거인명부등재자 기재값": 0,
        })
    return pd.DataFrame(rows)

def audit_table(df):
    result_rows = []

    for _, row in df.iterrows():
        election = row["선거명"]

        received = to_int(row["수령매수"])
        start_no = to_int(row["잔여 시작번호"])
        end_no = to_int(row["잔여 끝번호"])
        damaged = to_int(row["오·훼손 미교부"])

        written_left = to_int(row["잔여매수 기재값"])
        written_issued = to_int(row["교부매수 기재값"])
        written_voters = to_int(row["투표자수계 기재값"])

        home_return = to_int(row["거소 미발송·반송"])
        decision_doc = to_int(row["결정서 지참"])
        envelope_return = to_int(row["거소투표용지·회송봉투 반납"])
        overseas = to_int(row["귀국투표자"])
        written_registry = to_int(row["선거인명부등재자 기재값"])

        # 1. 잔여매수 계산
        if start_no > 0 and end_no >= start_no:
            calc_left = end_no - start_no + 1 + damaged
        else:
            calc_left = 0

        # 2. 교부매수 계산
        if received >= calc_left:
            calc_issued = received - calc_left
        else:
            calc_issued = -1

        # 3. 투표자수계 = 교부매수
        # 4. 선거인명부등재자 = 투표자수계 - 특수유형 투표자
        special_total = home_return + decision_doc + envelope_return + overseas
        calc_registry = written_voters - special_total

        check_left = calc_left == written_left
        check_issued = calc_issued == written_issued
        check_voters = written_voters == written_issued
        check_registry = calc_registry == written_registry

        problems = []
        if not check_left:
            problems.append(f"잔여매수 불일치: 계산 {calc_left:,} / 기재 {written_left:,}")
        if not check_issued:
            problems.append(f"교부매수 불일치: 계산 {calc_issued:,} / 기재 {written_issued:,}")
        if not check_voters:
            problems.append(f"투표자수계 불일치: 투표자수계 {written_voters:,} / 교부매수 {written_issued:,}")
        if not check_registry:
            problems.append(f"선거인명부등재자 불일치: 계산 {calc_registry:,} / 기재 {written_registry:,}")

        result_rows.append({
            "선거명": election,
            "잔여매수 계산값": calc_left,
            "교부매수 계산값": calc_issued,
            "특수유형 합계": special_total,
            "선거인명부등재자 계산값": calc_registry,
            "잔여검산": "OK" if check_left else "오류",
            "교부검산": "OK" if check_issued else "오류",
            "투표자수검산": "OK" if check_voters else "오류",
            "명부등재자검산": "OK" if check_registry else "오류",
            "최종판정": "정상" if len(problems) == 0 else "재확인",
            "비고": "이상 없음" if len(problems) == 0 else " / ".join(problems),
        })

    return pd.DataFrame(result_rows)

# -----------------------------
# 화면 시작
# -----------------------------
st.markdown('<div class="main-title">🗳️ 투표록 7개 선거<br>빠른 심사 앱</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-text">모바일 GitHub 업로드 전용 3파일 버전입니다. 사진을 올리고 숫자를 입력하면 7개 선거를 자동 검산합니다.</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="notice">
<b>현재 버전 안내</b><br>
① GitHub에 <b>app.py / requirements.txt / README.md</b> 3개 파일만 올리면 됩니다.<br>
② 사진은 참고용으로 표시됩니다.<br>
③ OCR 자동 인식은 다음 단계에서 추가합니다.<br>
④ 현재는 표에 숫자를 직접 입력하거나 확인·수정하면 자동 검산됩니다.
</div>
""", unsafe_allow_html=True)

# -----------------------------
# 사진 입력
# -----------------------------
st.markdown('<div class="step-title">📷 1. 투표록 사진 올리기</div>', unsafe_allow_html=True)

tab_file, tab_camera = st.tabs(["📁 사진 선택", "📷 카메라 촬영"])
uploaded_image = None

with tab_file:
    uploaded_image = st.file_uploader(
        "갤러리에서 투표록 사진을 선택하세요.",
        type=["jpg", "jpeg", "png"]
    )

with tab_camera:
    camera_image = st.camera_input("카메라로 투표록을 촬영하세요.")
    if camera_image is not None:
        uploaded_image = camera_image

if uploaded_image is not None:
    image = Image.open(uploaded_image).convert("RGB")
    st.image(image, caption="업로드된 투표록 이미지", use_container_width=True)

    width, height = image.size
    st.caption(f"이미지 크기: {width} × {height}")

    if width < 1000 or height < 1000:
        st.warning("사진 해상도가 낮을 수 있습니다. 더 가까이, 더 선명하게 촬영해 주세요.")

# -----------------------------
# 입력표
# -----------------------------
st.markdown('<div class="step-title">🧾 2. 선거별 숫자 입력</div>', unsafe_allow_html=True)

st.markdown("""
<div class="small-guide">
<b>입력 순서</b><br>
1. 잔여 투표용지의 시작번호와 끝번호를 입력합니다.<br>
2. 오·훼손 미교부 투표용지가 있으면 입력합니다.<br>
3. 투표록에 기재된 잔여매수, 교부매수, 투표자수계를 입력합니다.<br>
4. 특수유형 투표자 수를 입력하면 선거인명부등재자를 자동 검산합니다.
</div>
""", unsafe_allow_html=True)

input_df = make_default_table()

edited_df = st.data_editor(
    input_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    column_config={
        "선거명": st.column_config.TextColumn("선거명", disabled=True),
        "수령매수": st.column_config.NumberColumn("수령매수", min_value=0, step=1),
        "잔여 시작번호": st.column_config.NumberColumn("잔여 시작번호", min_value=0, step=1),
        "잔여 끝번호": st.column_config.NumberColumn("잔여 끝번호", min_value=0, step=1),
        "오·훼손 미교부": st.column_config.NumberColumn("오·훼손 미교부", min_value=0, step=1),
        "잔여매수 기재값": st.column_config.NumberColumn("잔여매수 기재값", min_value=0, step=1),
        "교부매수 기재값": st.column_config.NumberColumn("교부매수 기재값", min_value=0, step=1),
        "투표자수계 기재값": st.column_config.NumberColumn("투표자수계 기재값", min_value=0, step=1),
        "거소 미발송·반송": st.column_config.NumberColumn("거소 미발송·반송", min_value=0, step=1),
        "결정서 지참": st.column_config.NumberColumn("결정서 지참", min_value=0, step=1),
        "거소투표용지·회송봉투 반납": st.column_config.NumberColumn("거소투표용지·회송봉투 반납", min_value=0, step=1),
        "귀국투표자": st.column_config.NumberColumn("귀국투표자", min_value=0, step=1),
        "선거인명부등재자 기재값": st.column_config.NumberColumn("선거인명부등재자 기재값", min_value=0, step=1),
    }
)

# -----------------------------
# 결과
# -----------------------------
st.markdown('<div class="step-title">✅ 3. 자동 심사 결과</div>', unsafe_allow_html=True)

result_df = audit_table(edited_df)

ok_count = int((result_df["최종판정"] == "정상").sum())
bad_count = int((result_df["최종판정"] == "재확인").sum())

col1, col2, col3 = st.columns(3)
col1.metric("전체 선거", len(result_df))
col2.metric("정상", ok_count)
col3.metric("재확인", bad_count)

st.dataframe(result_df, use_container_width=True, hide_index=True)

if bad_count == 0:
    st.markdown('<div class="ok-box"><b>7개 선거 모두 검산 결과 정상입니다.</b></div>', unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="bad-box"><b>재확인 필요한 선거가 있습니다.</b><br>비고란의 불일치 항목을 원본 투표록과 대조해 주세요.</div>',
        unsafe_allow_html=True
    )

csv = result_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="📄 심사결과 CSV 다운로드",
    data=csv,
    file_name="투표록_심사결과.csv",
    mime="text/csv",
    use_container_width=True
)

# -----------------------------
# 촬영 안내
# -----------------------------
st.markdown('<div class="step-title">📌 촬영 안내</div>', unsafe_allow_html=True)
st.markdown("""
<div class="small-guide">
1. 문서를 책상 위에 평평하게 놓아 주세요.<br>
2. 그림자가 생기지 않도록 밝은 곳에서 촬영해 주세요.<br>
3. 투표록 표 전체가 화면 안에 들어오도록 촬영해 주세요.<br>
4. 숫자가 흐리게 보이면 다시 촬영해 주세요.<br>
5. OCR 자동 인식 버전에서도 최종 결과는 원본 투표록과 대조해야 합니다.
</div>
""", unsafe_allow_html=True)

st.caption("※ 본 앱은 투표록 심사 보조용입니다. 최종 판단은 공식 선거관리 절차와 원본 서류 확인에 따릅니다.")
