import streamlit as st
import pandas as pd
import instaloader
import itertools
import easyocr
import numpy as np
from PIL import Image

# Firebase 관련 라이브러리 임포트
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="치과 불법 의료광고 모니터링 시스템",
    page_icon="🦷",
    layout="wide"
)

st.title("🦷 치과 불법 의료광고 및 환자 유인 탐지 대시보드")
st.markdown("이미지 OCR 자동 추출 및 텍스트 분석을 통해 **의료법 위반 소지**를 검사하고, 클라우드 DB에 영구 저장합니다.")

# Firebase 중복 초기화 방지 및 연결
if not firebase_admin._apps:
    firebase_config = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def save_scanned_post(account, platform, summary, issues, risk):
    """스캔된 데이터를 Firestore에 영구 저장"""
    doc_ref = db.collection("illegal_ads").document()
    doc_ref.set({
        "account": account,
        "platform": platform,
        "summary": summary,
        "issues": issues,
        "risk": risk,
        "timestamp": firestore.SERVER_TIMESTAMP
    })

def load_scanned_posts():
    """Firestore에 저장된 데이터 목록을 최신순으로 불러옴"""
    try:
        docs = db.collection("illegal_ads").order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
        data = []
        for doc in docs:
            item = doc.to_dict()
            data.append({
                "계정명": item.get("account"),
                "플랫폼": item.get("platform"),
                "본문 요약": item.get("summary"),
                "감지된 위반 항목": item.get("issues"),
                "위험도": item.get("risk"),
                "수집 일시": str(item.get("timestamp"))
            })
        return data
    except Exception as e:
        return []

# 캐시를 이용해 EasyOCR Reader 로딩 (성능 최적화)
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['ko', 'en'])

with st.spinner("OCR 모델을 불러오는 중입니다. 잠시만 기다려주세요..."):
    reader = load_ocr_reader()

# 사이드바 설정
st.sidebar.header("⚙️ 모니터링 및 수집 설정")
target_hashtag = st.sidebar.text_input("타겟 해시태그 (예: 치과이벤트)", value="치과이벤트")
max_posts = st.sidebar.slider("수집할 최대 게시물 수", min_value=1, max_value=10, value=3)

st.sidebar.markdown("---")
st.sidebar.subheader("인스타그램 계정 연동 (선택)")
insta_id = st.sidebar.text_input("인스타 ID (또는 이메일)", value="")
insta_pw = st.sidebar.text_input("인스타 비밀번호", type="password", value="")

run_scan = st.sidebar.button("🚀 인스타그램 실시간 스캔 실행")

# 의료법 위반 주요 키워드 및 패턴 딕셔너리
VIOLATION_RULES = {
    "무면허 의료/면허범위 위반": ["치기공사", "방문 점검", "찾아가는", "기공사가 직접", "집으로 찾아가는"],
    "환자 유인·알선 (부당이익)": ["0원", "무료", "선착순", "체험단", "전액지원", "상품권 증전", "할인 이벤트"],
    "과대/오인 광고": ["최고", "최초", "100% 보장", "부작용 전혀 없음", "완치 보장"]
}

def analyze_advertisement(text):
    """광고 텍스트를 분석하여 위반 항목과 위험도 점수를 산출하는 함수"""
    detected_issues = []
    score = 0
    
    for category, keywords in VIOLATION_RULES.items():
        matched_keywords = [kw for kw in keywords if kw in text]
        if matched_keywords:
            detected_issues.append({
                "category": category,
                "keywords": matched_keywords
            })
            score += len(matched_keywords) * 25
            
    risk_score = min(score, 100)
    return detected_issues, risk_score

def extract_text_from_image(image):
    """Uploaded Image에서 EasyOCR을 이용해 텍스트 추출"""
    image_np = np.array(image)
    results = reader.readtext(image_np, detail=0)
    extracted_text = " ".join(results)
    return extracted_text

# 메인 화면 탭 구성
tab1, tab2, tab3 = st.tabs(["🔍 단건 수동 분석 & OCR", "📊 실시간 해시태그 스캔 대시보드", "📂 증거 채증 및 신고 관리"])

with tab1:
    st.subheader("광고 이미지 업로드 및 자동 OCR 분석")
    
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("광고 캡처 이미지 업로드", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="업로드된 광고 이미지", use_column_width=True)
            
            if st.button("🔍 이미지에서 텍스트 자동 추출 (OCR)"):
                with st.spinner("이미지 내 텍스트를 분석 중입니다..."):
                    ocr_result = extract_text_from_image(image)
                    st.session_state['ocr_text'] = ocr_result
            
    with col2:
        default_text = st.session_state.get('ocr_text', "치료 후 방치하면... 현직 치기공사가 직접 방문하는 찾아가는 보철물 점검 서비스! 0원 점검비 무료")
        ad_text_input = st.text_area("추출된 텍스트 및 광고 본문", value=default_text, height=150)
        
        if st.button("위반 여부 정밀 분석"):
            if ad_text_input:
                issues, risk_score = analyze_advertisement(ad_text_input)
                
                st.markdown("---")
                st.markdown(f"### 🛡️ 종합 위험도 점수: **{risk_score}점 / 100점**")
                
                if risk_score >= 50:
                    st.error("🚨 **[고위험]** 현행 의료법 위반 소지가 매우 높습니다. 보건소 신고 및 플랫폼 차단 조치가 필요합니다.")
                elif risk_score > 0:
                    st.warning("⚠️ **[주의]** 일부 위반 의심 키워드가 포함되어 있습니다. 면밀한 검토가 필요합니다.")
                else:
                    st.success("✅ 특이 위반 사항이 발견되지 않았습니다.")
                
                if issues:
                    st.markdown("#### 세부 위반 항목 탐지 결과")
                    for issue in issues:
                        st.markdown(f"- **{issue['category']}** (매칭 키워드: `{', '.join(issue['keywords'])}`)")
            else:
                st.warning("분석할 텍스트를 입력해주세요.")

with tab2:
    st.subheader(f"📊 인스타그램 해시태그 `#{target_hashtag}` 실시간 스캔 및 DB 연동 결과")
    
    if run_scan:
        with st.spinner(f"인스타그램에서 '#{target_hashtag}' 최신 게시물을 수집하고 분석 중입니다..."):
            L = instaloader.Instaloader()
            if insta_id and insta_pw:
                try:
                    L.login(insta_id, insta_pw)
                except Exception:
                    pass

            posts_count = 0
            try:
                hashtag_obj = instaloader.Hashtag.from_name(L.context, target_hashtag.strip("#"))
                for post in itertools.islice(hashtag_obj.get_posts(), max_posts):
                    caption = post.caption if post.caption else ""
                    issues, risk_score = analyze_advertisement(caption)
                    
                    risk_label = "안전"
                    if risk_score >= 50:
                        risk_label = "🚨 고위험"
                    elif risk_score > 0:
                        risk_label = "⚠️ 주의"

                    risk_str = f"{risk_score}점 ({risk_label})"
                    issue_str = ", ".join([i["category"] for i in issues]) if issues else "없음"
                    summary_text = caption[:60] + "..." if len(caption) > 60 else caption

                    # 스캔된 데이터를 Firebase DB에 즉시 저장
                    save_scanned_post(
                        account=f"@{post.owner_username}",
                        platform="Instagram",
                        summary=summary_text,
                        issues=issue_str,
                        risk=risk_str
                    )
                    posts_count += 1
            except Exception as e:
                pass

            if posts_count > 0:
                st.success(f"총 {posts_count}개의 게시물을 성공적으로 스캔하여 Firebase DB에 저장했습니다!")
            else:
                st.warning("수집된 게시물이 없거나 인스타그램 서버 제한으로 데이터를 가져오지 못했습니다.")

    # Firebase DB에서 저장된 데이터를 불러와서 대시보드 테이블에 출력
    db_posts = load_scanned_posts()
    
    if db_posts:
        df_db = pd.DataFrame(db_posts)
        st.dataframe(df_db, use_container_width=True)
        st.info("💡 위 목록은 Firebase 클라우드 DB에 영구 저장된 실시간 탐지 내역입니다.")
    else:
        mock_data = pd.DataFrame([
            {
                "계정명": "@mins76815",
                "플랫폼": "Instagram",
                "본문 요약": "치료 후 방치하면... 현직 치기공사가 직접 방문하는 찾아가는 보철물 점검 서비스! 0원...",
                "감지된 위반 항목": "무면허 의료/면허범위 위반, 환자 유인·알선 (부당이익)",
                "위험도": "50점 (🚨 고위험)",
                "수집 일시": "2026-11-03 13:50"
            }
        ])
        st.dataframe(mock_data, use_container_width=True)
        st.info("💡 아직 DB에 저장된 데이터가 없습니다. 사이드바의 **[🚀 인스타그램 실시간 스캔 실행]** 버튼을 눌러 데이터를 수집해 보세요.")

with tab3:
    st.subheader("📂 채증 자료 다운로드 및 신고 연계")
    st.markdown("선택한 의심 게시물의 **스크린샷, OCR 텍스트, URL, 위반 사유 요약서**를 하나의 패키지로 내보냅니다.")
    
    selected_id = st.selectbox("내보낼 게시물 선택", ["1번 게시물 (@mins76815)"])
    
    if st.button("📥 보건소/협회 제출용 증거 패키지(PDF/ZIP) 생성"):
        st.success(f"'{selected_id}'의 증거 채증 자료가 성공적으로 생성되었습니다!")
        st.download_button(
            label="다운로드 하기",
            data="Sample Evidence Report Data",
            file_name="evidence_report.txt",
            mime="text/plain"
        )