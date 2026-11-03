import streamlit as st
import pandas as pd

# 페이지 레이아웃 설정
st.set_page_config(
    page_title="치과 불법 의료광고 모니터링 시스템",
    page_icon="🦷",
    layout="wide"
)

st.title("🦷 치과 불법 의료광고 및 환자 유인 탐지 대시보드")
st.markdown("인스타그램 등 SNS 광고 텍스트 및 이미지 OCR 결과를 분석하여 **의료법 위반 소지**를 자동으로 검사합니다.")

# 사이드바 설정
st.sidebar.header("⚙️ 모니터링 설정")
target_hashtag = st.sidebar.text_input("타겟 해시태그", value="#치과이벤트 #보철물점검 #임플란트할인")
scan_interval = st.sidebar.selectbox("자동 스캔 주기", ["1시간 마다", "매일 1회", "수동 실행"])
run_scan = st.sidebar.button("🚀 스캔 및 분석 실행")

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

# 메인 화면 탭 구성
tab1, tab2, tab3 = st.tabs(["🔍 단건 수동 분석", "📊 실시간 모니터링 대시보드", "📂 증거 채증 및 신고 관리"])

with tab1:
    st.subheader("광고 게시물 수동 분석기")
    
    col1, col2 = st.columns(2)
    with col1:
        uploaded_file = st.file_uploader("광고 캡처 이미지 업로드", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.image(uploaded_file, caption="업로드된 광고 이미지", use_column_width=True)
            
    with col2:
        # 앞서 예시로 보신 문구를 기본값으로 설정
        default_text = "치료 후 방치하면... 현직 치기공사가 직접 방문하는 찾아가는 보철물 점검 서비스! 0원 점검비 무료"
        ad_text_input = st.text_area("광고 본문 및 OCR 추출 텍스트", value=default_text, height=150)
        
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
    st.subheader("📊 자동 수집된 의심 게시물 피드")
    
    # 가상의 탐지 데이터프레임 생성
    mock_data = pd.DataFrame([
        {
            "ID": 1,
            "계정명": "@mins76815",
            "플랫폼": "Instagram",
            "감지된 위반 항목": "무면허 의료조장, 환자유인(0원)",
            "위험도": "95점 (고위험)",
            "수집 일시": "2026-11-03 13:50"
        },
        {
            "ID": 2,
            "계정명": "@dental_event_zero",
            "플랫폼": "Instagram",
            "감지된 위반 항목": "환자 유인(선착순 무료)",
            "위험도": "75점 (주의)",
            "수집 일시": "2026-11-03 11:20"
        }
    ])
    
    st.dataframe(mock_data, use_container_width=True)
    st.info("💡 위 목록은 스크래핑 및 OCR 모듈을 통해 주기적으로 업데이트되는 의심 게시물 리스트입니다.")

with tab3:
    st.subheader("📂 채증 자료 다운로드 및 신고 연계")
    st.markdown("선택한 의심 게시물의 **스크린샷, OCR 텍스트, URL, 위반 사유 요약서**를 하나의 패키지로 내보냅니다.")
    
    selected_id = st.selectbox("내보낼 게시물 선택", ["1번 게시물 (@mins76815)", "2번 게시물 (@dental_event_zero)"])
    
    if st.button("📥 보건소/협회 제출용 증거 패키지(PDF/ZIP) 생성"):
        st.success(f"'{selected_id}'의 증거 채증 자료가 성공적으로 생성되었습니다!")
        st.download_button(
            label="다운로드 하기",
            data="Sample Evidence Report Data",
            file_name="evidence_report.txt",
            mime="text/plain"
        )