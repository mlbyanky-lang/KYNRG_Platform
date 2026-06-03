import streamlit as st
import pandas as pd
import random
import re
from datetime import datetime

st.set_page_config(page_title="김영편입 노량진 AI 통합 LMS", page_icon="🏫", layout="wide")

# ==========================================
# 0. 데이터 로드 및 누락/특수문자 가드 엔진
# ==========================================
@st.cache_data(ttl=60)
def load_data(file_type, book_choice):
    filename = f"{book_choice}_{file_type}.csv"
    try:
        df = pd.read_csv(filename, encoding='utf-8')
    except Exception:
        try:
            df = pd.read_csv(filename, encoding='utf-8-sig')
        except Exception:
            st.error(f"🚨 {filename} 파일을 시스템 내부에서 찾을 수 없습니다.")
            return pd.DataFrame()
            
    if not df.empty:
        try:
            # 컬럼명 양끝 공백 제거 및 소문자 정형화
            df.columns = df.columns.str.strip().str.lower()
            df = df.dropna(subset=['day'])
            df['day'] = pd.to_numeric(df['day'], errors='coerce').fillna(1).astype(int)
            df = df[df['day'] >= 1]
            return df.reset_index(drop=True)
        except Exception as e:
            st.error(f"🚨 데이터 가공 중 분석 오류 발생: {e}")
            return pd.DataFrame()
    return df

# ==========================================
# ⚙️ 편입 최적화 오답 메이커 (중복 절대 불가능 시스템)
# ==========================================
def build_quiz_options(correct_word, full_pool):
    """
    정답 단어 1개와 철자가 유사한 고유 오답 3개를 섞어 정확히 4개의 고유 보기 리스트를 반환합니다.
    Streamlit 중복 보기 에러를 완벽히 차단합니다.
    """
    correct_clean = str(correct_word).strip()
    
    # 전체 풀 정제 (소문자 변환 및 고유화)
    clean_pool = list(set([str(w).strip() for w in full_pool if pd.notna(w) and str(w).strip() != ""]))
    
    # 정답과 확실히 다른 오답 후보군 필터링 (대소문자 무시 매칭 차단)
    wrong_candidates = [w for w in clean_pool if w.lower() != correct_clean.lower()]
    
    # 1차 추적: 앞 두 글자가 같은 철자 유사 어휘 수집
    prefix = correct_clean.lower()[:2] if len(correct_clean) >= 2 else correct_clean.lower()
    similar_pool = [w for w in wrong_candidates if w.lower().startswith(prefix)]
    
    # 2차 추적: 철자 유사 어휘가 모자라면 길이가 비슷한 어휘 수집
    if len(similar_pool) < 3:
        similar_pool += [w for w in wrong_candidates if abs(len(w) - len(correct_clean)) <= 2 and w not in similar_pool]
        
    # 3차 추적: 그래도 모자라면 전체 오답 풀에서 수급
    if len(similar_pool) < 3:
        similar_pool += [w for w in wrong_candidates if w not in similar_pool]
        
    # 최종 무작위 오답 3개 확정
    chosen_wrongs = random.sample(similar_pool, min(3, len(similar_pool)))
    
    # 정답 + 오답 합치기 및 고유성 재검증
    final_options = list(set([correct_clean] + chosen_wrongs))
    
    # 만약 set 과정에서 4개가 안 채워졌다면 강제 채우기 패딩
    while len(final_options) < 4 and wrong_candidates:
        extra = random.choice(wrong_candidates)
        if extra not in final_options:
            final_options.append(extra)
            
    random.shuffle(final_options)
    return final_options

# ==========================================
# 1. 시스템 전역 변수 및 세션 상태 초기화
# ==========================================
if "mean_test_active" not in st.session_state: st.session_state.mean_test_active = False
if "mean_test_config" not in st.session_state: st.session_state.mean_test_config = {}

if "syn_test_active" not in st.session_state: st.session_state.syn_test_active = False
if "syn_test_config" not in st.session_state: st.session_state.syn_test_config = {}

if "announcements" not in st.session_state:
    st.session_state.announcements = {
        "CLASS E": ["금일 모의고사 오답노트 점검이 야간 자습 1교시에 있습니다."],
        "CLASS C": ["데일리 테스트 누적 미통과자는 재시험 대상입니다."],
        "CLASS BD": ["단어 암기 미달자는 의무 자습 시간 연장됩니다."],
        "CLASS BJ": ["과제 제출 마감은 금일 오후 10시까지입니다."],
        "CLASS A": ["최상위권 특별 고난도 어휘 배포 자료를 수령하세요."]
    }

if "students_dict" not in st.session_state:
    st.session_state.students_dict = {
        "CLASS E": ["김철수", "이영희", "박민수", "최재성", "정지원"],
        "CLASS C": ["강동우", "조현아", "윤서준", "한지민", "배수지"],
        "CLASS BD": ["고윤정", "송중기", "이도현", "임지연", "박서준"],
        "CLASS BJ": ["차은우", "한소희", "장원영", "정국", "뷔"],
        "CLASS A": ["홍길동", "성춘향", "이몽룡", "심청", "임꺽정"]
    }
if "exam_results" not in st.session_state: st.session_state.exam_results = []
if "exam_started" not in st.session_state: st.session_state.exam_started = False
if "current_questions" not in st.session_state: st.session_state.current_questions = []
if "current_exam_type" not in st.session_state: st.session_state.current_exam_type = ""

# ==========================================
# 2. 사이드바 네비게이션 (메뉴 완전 분리형)
# ==========================================
st.sidebar.title("🏫 김영편입 노량진")
menu = st.sidebar.radio("📌 시스템 메뉴 선택", [
    "📢 반별 공지사항", 
    "📖 데일리 암기장", 
    "📝 실전 뜻찾기 테스트", 
    "📝 실전 동의어 테스트", 
    "🔒 원장님 전용 대시보드"
])
st.sidebar.divider()
st.sidebar.caption("© 2026 김영편입 AI 학습 관리 시스템")

# ==========================================
# 3. 메뉴별 기능 구현
# ==========================================

if menu == "📢 반별 공지사항":
    st.title("📢 반별 학습 공지사항")
    student_class = st.selectbox("본인의 소속 반을 선택하세요:", list(st.session_state.students_dict.keys()))
    st.subheader(f"✨ {student_class} 오늘의 공지 목록")
    notices = st.session_state.announcements.get(student_class, [])
    if notices:
        for idx, notice in enumerate(notices):
            st.info(f"📌 **[{idx+1}]** {notice}")
    else:
        st.write("현재 등록된 공지사항이 없습니다.")

elif menu == "📖 데일리 암기장":
    st.title("📖 데일리 플래시 암기장")
    col1, col2 = st.columns(2)
    with col1: book_choice = st.selectbox("📚 단어 교재 선택:", ["MVP1", "MVP2"])
    
    df = load_data("뜻쓰기", book_choice)
    if not df.empty:
        days = sorted(df['day'].unique())
        with col2: target_day = st.selectbox("📅 진도 DAY 선택:", [f"DAY {d:02d}" for d in days])
        
        target_num = int(target_day.split()[1])
        day_df = df[df['day'] == target_num].reset_index(drop=True)
        
        st.success(f"🔥 {book_choice} - {target_day} 어휘 목록 (총 {len(day_df)}개 단어)")
        st.dataframe(day_df[['word', 'meaning']], use_container_width=True)

# --- [분리 메뉴 1] 실전 뜻찾기 테스트 ---
elif menu == "📝 실전 뜻찾기 테스트":
    st.title("📝 실전 뜻찾기 데일리 테스트")
    
    if not st.session_state.mean_test_active:
        st.warning("🔒 현재 활성화된 뜻찾기 시험이 없습니다. 원장님이 시험을 출제할 때까지 대기해 주세요.")
    else:
        config = st.session_state.mean_test_config
        st.info(f"🎯 **뜻찾기 활성 시험:** {config['book']} | **범위:** DAY {config['start']} ~ {config['end']} ({config['num_q']}문항)")
        
        col1, col2 = st.columns(2)
        with col1: s_class = st.selectbox("소속 반 선택:", list(st.session_state.students_dict.keys()), key="mean_class")
        with col2: s_name = st.selectbox("본인 이름 선택:", st.session_state.students_dict[s_class], key="mean_name")
        
        if not st.session_state.exam_started:
            if st.button("🚀 뜻찾기 시험 시작", use_container_width=True):
                raw_df = load_data("뜻쓰기", config['book'])
                if not raw_df.empty:
                    filtered_df = raw_df[(raw_df['day'] >= config['start']) & (raw_df['day'] <= config['end'])]
                    
                    if len(filtered_df) == 0:
                        st.error("지정 범위 내에 단어 데이터가 부족합니다.")
                    else:
                        unique_words = filtered_df['word'].drop_duplicates().tolist()
                        random.shuffle(unique_words)
                        q_count = min(config['num_q'], len(unique_words))
                        target_words = unique_words[:q_count]
                        
                        sampled_df = pd.concat([filtered_df[filtered_df['word'] == w].sample(n=1) for w in target_words]).reset_index(drop=True)
                        all_meanings = list(raw_df['meaning'].dropna().str.strip().unique())
                        
                        questions = []
                        for _, row in sampled_df.iterrows():
                            correct = str(row['meaning']).strip()
                            wrong_pool = [m for m in all_meanings if m != correct]
                            wrong = random.sample(wrong_pool, min(3, len(wrong_pool)))
                            options = [correct] + wrong
                            random.shuffle(options)
                            questions.append({
                                'title': f"`{row['word']}` 의 뜻으로 가장 알맞은 것은?",
                                'context': None,
                                'options': options,
                                'correct': correct
                            })
                        
                        st.session_state.current_questions = questions
                        st.session_state.current_exam_type = "뜻찾기"
                        st.session_state.exam_started = True
                        st.rerun()
                        
        if st.session_state.exam_started and st.session_state.current_exam_type == "뜻찾기":
            st.subheader(f"✍️ {s_name} 학생의 뜻찾기 시험지")
            with st.form("mean_exam_form"):
                student_answers = []
                for i, q in enumerate(st.session_state.current_questions):
                    st.markdown(f"##### **[Q{i+1}]** {q['title']}")
                    user_ans = st.radio(f"보기 선택 (Q{i+1})", q['options'], key=f"mean_ans_{i}", index=None, label_visibility="collapsed")
                    student_answers.append(user_ans)
                    st.divider()
                
                if st.form_submit_button("🎯 최종 답안 제출 및 자동 채점"):
                    if None in student_answers:
                        st.warning("⚠️ 풀지 않은 문항이 있습니다. 모든 문제의 답을 체크해 주세요.")
                    else:
                        correct_count = sum([1 for u_a, q in zip(student_answers, st.session_state.current_questions) if u_a == q['correct']])
                        score = int((correct_count / len(student_answers)) * 100)
                        
                        st.session_state.exam_results.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "class": s_class, "name": s_name, "type": "뜻찾기",
                            "test_name": f"{config['book']}_DAY{config['start']}~{config['end']}", "score": score
                        })
                        st.balloons()
                        st.success(f"💯 제출 완료! {s_name} 학생의 점수는 **{score}점**입니다.")
                        st.session_state.exam_started = False
                        st.session_state.current_questions = []

# --- [분리 메뉴 2] 실전 동의어 테스트 ---
elif menu == "📝 실전 동의어 테스트":
    st.title("📝 실전 동의어 문맥 추론 테스트")
    
    if not st.session_state.syn_test_active:
        st.warning("🔒 현재 활성화된 동의어 문맥 시험이 없습니다. 원장님이 시험을 출제할 때까지 대기해 주세요.")
    else:
        config = st.session_state.syn_test_config
        st.info(f"🎯 **동의어 활성 시험:** {config['book']} | **범위:** DAY {config['start']} ~ {config['end']} ({config['num_q']}문항)")
        
        col1, col2 = st.columns(2)
        with col1: s_class = st.selectbox("소속 반 선택:", list(st.session_state.students_dict.keys()), key="syn_class")
        with col2: s_name = str(st.selectbox("본인 이름 선택:", st.session_state.students_dict[s_class], key="syn_name"))
        
        if not st.session_state.exam_started:
            if st.button("🚀 동의어 문맥 시험 시작", use_container_width=True):
                raw_df = load_data("동의어", config['book'])
                if not raw_df.empty:
                    filtered_df = raw_df[(raw_df['day'] >= config['start']) & (raw_df['day'] <= config['end'])]
                    
                    if len(filtered_df) == 0:
                        st.error("지정 범위 내에 단어 데이터가 부족합니다.")
                    else:
                        # 표제어 문제 단어 자체의 중복을 배제
                        unique_words = filtered_df['word'].drop_duplicates().tolist()
                        random.shuffle(unique_words)
                        q_count = min(config['num_q'], len(unique_words))
                        target_words = unique_words[:q_count]
                        
                        sampled_df = pd.concat([filtered_df[filtered_df['word'] == w].sample(n=1) for w in target_words]).reset_index(drop=True)
                        
                        # 동의어 컬럼(synonym 1~5) 추적
                        syn_cols = [c for c in raw_df.columns if 'synonym' in c]
                        
                        # 교재 전체에서 오답으로 조립할 유효 풀 구성
                        all_syns_pool = []
                        for col in syn_cols:
                            if col in raw_df.columns:
                                all_syns_pool += raw_df[col].dropna().astype(str).str.strip().tolist()
                        all_syns_pool = list(set(all_syns_pool))
                        
                        questions = []
                        for _, row in sampled_df.iterrows():
                            # 해당 단어 행의 유효 정답 수집
                            row_syns = []
                            for col in syn_cols:
                                if col in row and pd.notna(row[col]) and str(row[col]).strip() != "":
                                    val = str(row[col]).strip()
                                    if val.lower() not in ['nan', 'none', '']:
                                        row_syns.append(val)
                            
                            # 동의어가 비어있을 시 가드 코드
                            if not row_syns: 
                                row_syns = [str(row['word']).strip()]
                            
                            # 1. 동의어 중 1개를 랜덤하게 정답으로 확정
                            correct = random.choice(row_syns)
                            
                            # 2. [💥 버그 박멸] 중복 에러가 절대 나지 않는 4지선다형 철자 유사 보기 조립
                            options = build_quiz_options(correct, all_syns_pool)
                            
                            # 3. 예문 하이라이트
