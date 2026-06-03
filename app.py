import streamlit as st
import pandas as pd
import random
import re
from datetime import datetime

st.set_page_config(page_title="김영편입 노량진 AI 통합 LMS", page_icon="🏫", layout="wide")

# ==========================================
# 0. 정제형 내부 로컬 데이터 로드 엔진
# ==========================================
@st.cache_data(ttl=60)
def load_data(file_type, book_choice):
    filename = f"{book_choice}_{file_type}.csv"
    try:
        df = pd.read_csv(filename, encoding='utf-8')
        return df
    except Exception as e:
        try:
            df = pd.read_csv(filename, encoding='utf-8-sig')
            return df
        except Exception as e2:
            st.error(f"🚨 {filename} 파일을 시스템 내부에서 찾을 수 없습니다.")
            return pd.DataFrame()

# ==========================================
# 1. 전역 시스템 제어 및 DB 초기화 (Session State)
# ==========================================
if "test_active" not in st.session_state: st.session_state.test_active = False
if "test_config" not in st.session_state: st.session_state.test_config = {}
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

# ==========================================
# 2. 사이드바 메뉴 대시보드
# ==========================================
st.sidebar.title("🏫 김영편입 노량진")
menu = st.sidebar.radio("📌 시스템 메뉴 선택", [
    "📢 반별 공지사항", 
    "📖 데일리 암기장", 
    "📝 실전 단어 테스트", 
    "🔒 원장님 전용 대시보드"
])
st.sidebar.divider()
st.sidebar.caption("© 2026 김영편입 AI 학습 관리 시스템")

# ==========================================
# 3. 메뉴별 기능 완벽 구현부
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
        # 데이터 유실 방지 및 최소 1 보정
        df['day_clean'] = df['day'].astype(str).str.extract(r'(\d+)').fillna(1).astype(int).clip(lower=1)
        days = sorted(df['day_clean'].unique())
        with col2: target_day = st.selectbox("📅 진도 DAY 선택:", [f"DAY {d:02d}" for d in days])
        
        target_num = int(target_day.split()[1])
        day_df = df[df['day_clean'] == target_num].reset_index(drop=True)
        
        st.success(f"🔥 {book_choice} - {target_day} 어휘 목록 (총 {len(day_df)}개 단어)")
        st.dataframe(day_df[['word', 'meaning']], use_container_width=True)

elif menu == "📝 실전 단어 테스트":
    st.title("📝 실전 데일리 단어 테스트")
    
    if not st.session_state.test_active:
        st.warning("🔒 현재 활성화된 학원 시험이 없습니다. 원장님이 관리자 페이지에서 시험을 배포할 때까지 대기해 주세요.")
    else:
        config = st.session_state.test_config
        st.info(f"🎯 **오늘의 활성 시험:** {config['book']} [{config['type']}] | **범위:** DAY {config['start']} ~ {config['end']} ({config['num_q']}문항)")
        
        col1, col2 = st.columns(2)
        with col1: s_class = st.selectbox("소속 반 선택:", list(st.session_state.students_dict.keys()))
        with col2: s_name = st.selectbox("본인 이름 선택:", st.session_state.students_dict[s_class])
        
        if not st.session_state.exam_started:
            if st.button("🚀 실시간 시험지 생성 및 시작"):
                raw_df = load_data(config['type'], config['book'])
                if not raw_df.empty:
                    raw_df['day_clean'] = raw_df['day'].astype(str).str.extract(r'(\d+)').fillna(1).astype(int).clip(lower=1)
                    filtered_df = raw_df[(raw_df['day_clean'] >= config['start']) & (raw_df['day_clean'] <= config['end'])]
                    
                    if len(filtered_df) == 0:
                        st.error("지정 범위 내에 단어 데이터가 부족합니다.")
                    else:
                        q_count = min(config['num_q'], len(filtered_df))
                        sampled_df = filtered_df.sample(n=q_count).reset_index(drop=True)
                        
                        questions = []
                        if config['type'] == "뜻쓰기":
                            all_meanings = raw_df['meaning'].dropna().unique().tolist()
                            for _, row in sampled_df.iterrows():
                                correct = row['meaning']
                                wrong = random.sample([m for m in all_meanings if m != correct], min(3, len(all_meanings)-1))
                                options = [correct] + wrong
                                random.shuffle(options)
                                questions.append({
                                    'title': f"`{row['word']}` 의 뜻으로 가장 알맞은 것은?",
                                    'context': None,
                                    'options': options,
                                    'correct': correct
                                })
                        else:
                            all_syns = raw_df['synonym 1'].dropna().unique().tolist()
                            for _, row in sampled_df.iterrows():
                                correct = row['synonym 1']
                                wrong = random.sample([s for s in all_syns if s != correct], min(3, len(all_syns)-1))
                                options = [correct] + wrong
                                random.shuffle(options)
                                
                                word = str(row['word'])
                                sentence = str(row['example sentence'])
                                highlighted_sentence = re.sub(f"({re.escape(word)})", r"<u><b>\1</b></u>", sentence, flags=re.IGNORECASE)
                                
                                questions.append({
                                    'title': f"다음 문장의 밑줄 친 단어와 **가장 문맥상 뜻이 가까운 동의어**를 고르시오.",
                                    'context': highlighted_sentence,
                                    'options': options,
                                    'correct': correct
                                })
                        
                        st.session_state.current_questions = questions
                        st.session_state.exam_started = True
                        st.rerun()
        
        if st.session_state.exam_started:
            st.subheader(f"✍️ {s_name} 학생의 시험지")
            with st.form("exam_paper_form"):
                student_answers = []
                for i, q in enumerate(st.session_state.current_questions):
                    st.markdown(f"##### **[Q{i+1}]** {q['title']}")
                    if q['context']:
                        st.markdown(f"> {q['context']}", unsafe_allow_html=True)
                    user_ans = st.radio(f"보기 선택 (Q{i+1})", q['options'], key=f"ans_{i}", index=None, label_visibility="collapsed")
                    student_answers.append(user_ans)
                    st.divider()
                
                submit_exam = st.form_submit_button("🎯 최종 답안 제출 및 자동 채점")
                if submit_exam:
                    if None in student_answers:
                        st.warning("⚠️ 아직 풀지 않은 문항이 있습니다.")
                    else:
                        correct_count = 0
                        for u_a, q in zip(student_answers, st.session_state.current_questions):
                            if u_a == q['correct']: correct_count += 1
                        
                        score = int((correct_count / len(student_answers)) * 100)
                        new_result = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "class": s_class,
                            "name": s_name,
                            "test_name": f"{config['book']}_{config['type']}_DAY{config['start']}~{config['end']}",
                            "score": score
                        }
                        st.session_state.exam_results.append(new_result)
                        st.balloons()
                        st.success(f"💯 채점 완료! 점수: **{score}점**")
                        st.session_state.exam_started = False
                        st.session_state.current_questions = []

elif menu == "🔒 원장님 전용 대시보드":
    st.title("🔒 원장님 전용 통합 관리 시스템")
    if "admin_authenticated" not in st.session_state: st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        admin_pw = st.text_input("원장님 마스터 비밀번호를 입력하세요:", type="password")
        if st.button("로그인"):
            if admin_pw == "1234":
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")
    else:
        if st.button("🔓 로그아웃", size="small"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        tab1, tab2, tab3 = st.tabs(["📝 데일리 테스트 배포 설정", "📊 실시간 성적 및 미응시생 파악", "👨‍🎓 학생 명부 & 공지 제어"])
        
        with tab1:
            st.subheader("📢 실시간 데일리 테스트 출제 설정")
            b_type = st.selectbox("1. 시험 유형 선택", ["뜻 맞추기", "동의어 예문 문맥형"])
            book = st.selectbox("2. 대상 어휘 교재 선택", ["MVP1", "MVP2"])
            
            # 💡 여기에서 최소값을 1로 강제 고정 보정했습니다.
            start_day, end_day = st.slider("3. 출제 진도 범위 지정 (DAY)", min_value=1, max_value=60, value=(1, 10), step=1)
            num_q = st.number_input("4. 출제할 총 문제 문항 수 지정", min_value=5, max_value=100, value=20, step=5)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 지정 조건으로 전 학생 시험 활성화", use_container_width=True):
                    st.session_state.test_active = True
                    st.session_state.test_config = {
                        "type": "뜻쓰기" if b_type == "뜻 맞추기" else "동의어",
                        "book": book,
                        "start": start_day,
                        "end": end_day,
                        "num_q": num_q
                    }
                    st.success("✅ 실시간 시험 배포 성공!")
            with col2:
                if st.button("🛑 현재 진행 중인 시험 마감 및 회수", use_container_width=True):
                    st.session_state.test_active = False
                    st.info("현재 배포 중인 시험이 마감되었습니다.")
        
        with tab2:
            st.subheader("📈 실시간 성적 분석 및 미응시생 현황")
            if not st.session_state.exam_results:
                st.info("아직 시험을 제출한 학생이 없습니다.")
            else:
                res_df = pd.DataFrame(st.session_state.exam_results)
                avg_scores = res_df.groupby("class")["score"].mean().reset_index()
                st.markdown("#### **📊 반별 실시간 테스트 평균 점수**")
                st.bar_chart(data=avg_scores, x="class", y="score", use_container_width=True)
                
                st.markdown("#### **🚨 반별 실시간 미응시자 리스트**")
                target_class = st.selectbox("미응시자를 조회할 반을 선택하세요:", list(st.session_state.students_dict.keys()))
                
                all_class_students = st.session_state.students_dict[target_class]
                submitted_students = res_df[res_df['class'] == target_class]['name'].tolist()
                unsubmitted_students = [student for student in all_class_students if student not in submitted_students]
                
                if unsubmitted_students:
                    st.error(f"❌ **{target_class} 미응시 학생 ({len(unsubmitted_students)}명):** {', '.join(unsubmitted_students)}")
                else:
                    st.success(f"✅ **{target_class} 전원 시험 응시 완료 완료!**")
                
                st.dataframe(res_df, use_container_width=True)
                csv_data = res_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📥 전체 성적 데이터 엑셀(CSV) 다운로드", data=csv_data, file_name=f"Daily_Test_Results.csv", mime="text/csv")
        
        with tab3:
            st.subheader("👨‍🎓 학원 학생 명부 & 반별 공지 일괄 제어")
            c_choice = st.selectbox("관리할 반 선택:", list(st.session_state.students_dict.keys()))
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**[{c_choice}] 실시간 학생 명부 편집**")
                current_students_str = "\n".join(st.session_state.students_dict[c_choice])
                new_students_str = st.text_area("학생 이름을 한 줄에 한 명씩 입력하세요:", value=current_students_str, height=150)
                if st.button(f"💾 {c_choice} 명부 업데이트"):
                    st.session_state.students_dict[c_choice] = [name.strip() for name in new_students_str.split("\n") if name.strip()]
                    st.success(f"✅ 명부 업데이트 완료.")
            
            with col2:
                st.markdown(f"**[{c_choice}] 새로운 공지사항 추가**")
                new_notice = st.text_input("전달할 공지 내용 입력:")
                if st.button(f"📢 {c_choice} 공지 등록"):
                    if new_notice.strip():
                        st.session_state.announcements[c_choice].insert(0, new_notice.strip())
                        st.success("✅ 공지가 등록되었습니다.")
