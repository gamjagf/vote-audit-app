
import streamlit as st
import pandas as pd
from PIL import Image
import re
import requests
from io import BytesIO

st.set_page_config(
    page_title="투표록 7개 선거 OCR 자동심사 앱",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.block-container {padding-top:1rem; padding-bottom:2rem;}
.main-title {font-size:2.05rem; font-weight:900; line-height:1.25; color:#252936;}
.sub-text {font-size:1.05rem; color:#666; line-height:1.7;}
.notice {background:#eaf4ff; color:#075985; padding:1rem; border-radius:1rem; font-size:1.02rem; line-height:1.7; margin-top:1rem;}
.warn {background:#fff7ed; color:#9a3412; padding:1rem; border-radius:1rem; font-size:1.02rem; line-height:1.7; margin-top:1rem;}
.step-title {font-size:1.35rem; font-weight:850; margin-top:1.8rem; margin-bottom:.6rem;}
.ok-box {background:#eaf8ef; border-left:7px solid #22a35a; padding:1rem; border-radius:1rem; font-size:1.05rem;}
.bad-box {background:#fff0f0; border-left:7px solid #e5484d; padding:1rem; border-radius:1rem; font-size:1.05rem;}
.guide {background:#f7f7f8; padding:1rem; border-radius:1rem; line-height:1.8;}
</style>
""", unsafe_allow_html=True)

def to_int(value):
    try:
        if pd.isna(value):
            return 0
        return int(str(value).replace(",", "").strip())
    except Exception:
        return 0

def clean_number_text(text):
    text = str(text)
    replace_map = {
        "O": "0", "o": "0", "D": "0",
        "I": "1", "l": "1", "|": "1",
        "S": "5", "s": "5",
        "B": "8",
        ",": "",
        " ": ""
    }
    for k, v in replace_map.items():
        text = text.replace(k, v)
    return text

def extract_numbers_from_text(text):
    text = clean_number_text(text)
    nums = re.findall(r"\d+", text)
    out = []
    for n in nums:
        try:
            value = int(n)
            if 0 <= value <= 999999:
                out.append(value)
        except:
            pass
    return out

def run_ocr_space(image):
    """
    OCR.Space API를 이용한 가벼운 OCR 방식.
    EasyOCR처럼 무거운 라이브러리를 설치하지 않으므로 Streamlit Cloud 배포 실패 가능성이 낮다.
    """
    api_key = st.secrets.get("OCR_SPACE_API_KEY", "helloworld")

    # 이미지 용량 줄이기
    img = image.convert("RGB")
    max_width = 1800
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)))

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    buffer.seek(0)

    payload = {
        "apikey": api_key,
        "language": "kor",
        "isOverlayRequired": False,
        "OCREngine": 2,
        "scale": True,
        "detectOrientation": True,
    }

    files = {
        "file": ("vote_log.jpg", buffer, "image/jpeg")
    }

    response = requests.post(
        "https://api.ocr.space/parse/image",
        data=payload,
        files=files,
        timeout=60
    )
    data = response.json()

    if data.get("IsErroredOnProcessing"):
        error_msg = data.get("ErrorMessage", data.get("ErrorDetails", "OCR 처리 오류"))
        raise RuntimeError(str(error_msg))

    parsed = data.get("ParsedResults", [])
    if not parsed:
        return "", []

    text = "\n".join([p.get("ParsedText", "") for p in parsed])
    numbers = extract_numbers_from_text(text)
    return text, numbers

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

def auto_fill_from_numbers(numbers):
    df = make_default_table()

    candidates = [n for n in numbers if 0 <= n <= 999999]

    # 수령매수 후보: 500~20000 사이에서 가장 자주 등장하는 값
    received_pool = [n for n in candidates if 500 <= n <= 20000]
    default_received = 0
    if received_pool:
        s = pd.Series(received_pool)
        default_received = int(s.value_counts().index[0])

    for i in range(len(df)):
        df.loc[i, "수령매수"] = default_received

    # 자동입력 초안: OCR에서 찾은 숫자를 순서대로 배치
    fill_cols = [
        "잔여 시작번호",
        "잔여 끝번호",
        "잔여매수 기재값",
        "교부매수 기재값",
        "투표자수계 기재값",
        "선거인명부등재자 기재값",
    ]

    # 10 이상 값을 먼저 넣고, 0~9는 뒤로 보냄
    ordered = [n for n in candidates if n >= 10] + [n for n in candidates if n < 10]

    idx = 0
    for r in range(len(df)):
        for c in fill_cols:
            if idx < len(ordered):
                df.loc[r, c] = int(ordered[idx])
                idx += 1

    return df

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

        calc_left = end_no - start_no + 1 + damaged if start_no > 0 and end_no >= start_no else 0
        calc_issued = received - calc_left if received >= calc_left else -1
        special_total = home_return + decision_doc + envelope_return + overseas
        calc_registry = written_voters - special_total

        problems = []
        if calc_left != written_left:
            problems.append(f"잔여매수 불일치: 계산 {calc_left:,} / 기재 {written_left:,}")
        if calc_issued != written_issued:
            problems.append(f"교부매수 불일치: 계산 {calc_issued:,} / 기재 {written_issued:,}")
        if written_voters != written_issued:
            problems.append(f"투표자수계 불일치: 투표자수계 {written_voters:,} / 교부매수 {written_issued:,}")
        if calc_registry != written_registry:
            problems.append(f"선거인명부등재자 불일치: 계산 {calc_registry:,} / 기재 {written_registry:,}")

        result_rows.append({
            "선거명": election,
            "잔여매수 계산값": calc_left,
            "교부매수 계산값": calc_issued,
            "특수유형 합계": special_total,
            "선거인명부등재자 계산값": calc_registry,
            "잔여검산": "OK" if calc_left == written_left else "오류",
            "교부검산": "OK" if calc_issued == written_issued else "오류",
            "투표자수검산": "OK" if written_voters == written_issued else "오류",
            "명부등재자검산": "OK" if calc_registry == written_registry else "오류",
            "최종판정": "정상" if not problems else "재확인",
            "비고": "이상 없음" if not problems else " / ".join(problems),
        })
    return pd.DataFrame(result_rows)

st.markdown('<div class="main-title">🗳️ 투표록 7개 선거<br>OCR 자동심사 앱</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">가벼운 OCR API 방식입니다. Streamlit Cloud에서 무거운 OCR 라이브러리를 설치하지 않습니다.</div>', unsafe_allow_html=True)

st.markdown("""
<div class="notice">
<b>가벼운 OCR 버전</b><br>
① EasyOCR를 제거하여 배포 오류를 줄였습니다.<br>
② 사진을 OCR API로 보내 숫자를 인식합니다.<br>
③ 인식 숫자 목록을 표에 자동 입력 초안으로 반영합니다.<br>
④ 숫자는 반드시 원본과 비교해 확인·수정해 주세요.
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="warn">
<b>주의</b><br>
이 버전은 외부 OCR API를 사용합니다. 민감한 실제 선거문서를 테스트할 때는 기관 보안 기준을 먼저 확인해야 합니다.<br>
정식 업무용은 내부망 OCR 또는 승인된 OCR API로 교체하는 것이 안전합니다.
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="step-title">📷 1. 투표록 사진 올리기</div>', unsafe_allow_html=True)

tab_file, tab_camera = st.tabs(["📁 사진 선택", "📷 카메라 촬영"])
uploaded_image = None

with tab_file:
    uploaded_image = st.file_uploader("갤러리에서 투표록 사진을 선택하세요.", type=["jpg", "jpeg", "png"])

with tab_camera:
    camera_image = st.camera_input("카메라로 투표록을 촬영하세요.")
    if camera_image is not None:
        uploaded_image = camera_image

if "input_df" not in st.session_state:
    st.session_state.input_df = make_default_table()

if uploaded_image is not None:
    image = Image.open(uploaded_image).convert("RGB")
    st.image(image, caption="업로드된 투표록 이미지", use_container_width=True)

    st.markdown('<div class="step-title">🤖 2. OCR 숫자 자동 인식</div>', unsafe_allow_html=True)

    if st.button("🔍 OCR로 숫자 자동 인식하기", use_container_width=True):
        with st.spinner("OCR 숫자 인식 중입니다. 네트워크 상태에 따라 시간이 걸릴 수 있습니다."):
            try:
                full_text, numbers = run_ocr_space(image)
                st.session_state.ocr_text = full_text
                st.session_state.ocr_numbers = numbers
                st.session_state.input_df = auto_fill_from_numbers(numbers)

                if len(numbers) == 0:
                    st.warning("OCR이 숫자를 찾지 못했습니다. 표와 숫자가 더 크게 보이도록 다시 촬영해 주세요.")
                else:
                    st.success(f"OCR 숫자 인식 완료: {len(numbers)}개 숫자를 찾았습니다. 아래 표를 확인·수정해 주세요.")
            except Exception as e:
                st.error("OCR 실행 중 오류가 발생했습니다.")
                st.write(e)

if "ocr_numbers" in st.session_state:
    st.markdown('<div class="step-title">🔢 OCR 인식 숫자 목록</div>', unsafe_allow_html=True)
    st.write(st.session_state.ocr_numbers)

    with st.expander("OCR 원문 보기"):
        st.text(st.session_state.get("ocr_text", ""))

st.markdown('<div class="step-title">🧾 3. 선거별 숫자 확인·수정</div>', unsafe_allow_html=True)
st.markdown("""
<div class="guide">
OCR 자동 입력값은 사진 상태에 따라 틀릴 수 있습니다.<br>
반드시 원본 투표록과 비교하여 숫자를 확인·수정한 뒤 심사 결과를 보세요.
</div>
""", unsafe_allow_html=True)

edited_df = st.data_editor(
    st.session_state.input_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    key="audit_editor"
)

st.session_state.input_df = edited_df

st.markdown('<div class="step-title">✅ 4. 자동 심사 결과</div>', unsafe_allow_html=True)

result_df = audit_table(edited_df)

ok_count = int((result_df["최종판정"] == "정상").sum())
bad_count = int((result_df["최종판정"] == "재확인").sum())

c1, c2, c3 = st.columns(3)
c1.metric("전체 선거", len(result_df))
c2.metric("정상", ok_count)
c3.metric("재확인", bad_count)

st.dataframe(result_df, use_container_width=True, hide_index=True)

if bad_count == 0:
    st.markdown('<div class="ok-box"><b>7개 선거 모두 검산 결과 정상입니다.</b></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="bad-box"><b>재확인 필요한 선거가 있습니다.</b><br>비고란의 불일치 항목을 원본 투표록과 대조해 주세요.</div>', unsafe_allow_html=True)

csv = result_df.to_csv(index=False).encode("utf-8-sig")
st.download_button("📄 심사결과 CSV 다운로드", data=csv, file_name="투표록_심사결과.csv", mime="text/csv", use_container_width=True)

st.markdown('<div class="step-title">📌 촬영 안내</div>', unsafe_allow_html=True)
st.markdown("""
<div class="guide">
1. 숫자가 있는 표 부분을 화면에 크게 채워 촬영해 주세요.<br>
2. 그림자 없이 밝은 곳에서 촬영해 주세요.<br>
3. 초점이 맞지 않으면 숫자를 잘못 읽거나 읽지 못할 수 있습니다.<br>
4. 최종 판단 전에는 반드시 원본 투표록과 대조해 주세요.
</div>
""", unsafe_allow_html=True)

st.caption("※ 본 앱은 투표록 심사 보조용입니다. 최종 판단은 공식 선거관리 절차와 원본 서류 확인에 따릅니다.")
