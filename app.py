import streamlit as st
import os
from openai import AzureOpenAI
from azure.storage.blob import BlobServiceClient
import PyPDF2
from io import BytesIO
import re
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="AntBot - 팀 솔루션 도우미",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for cleaner UI
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .title-container {
        text-align: center;
        padding: 1rem 0 2rem 0;
    }
    .subtitle {
        color: #666;
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Azure 설정 초기화
@st.cache_resource
def init_azure_clients():
    """Azure OpenAI와 Blob Storage 클라이언트 초기화"""
    
    # Azure OpenAI 설정
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
    azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    # Blob Storage 설정
    blob_connection_string = os.getenv("AZURE_BLOB_CONNECTION_STRING")
    blob_container_name = os.getenv("AZURE_BLOB_CONTAINER_NAME", "antbot-docs")
    
    # 클라이언트 생성
    openai_client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=azure_api_key,
        api_version=azure_api_version
    )
    
    blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
    
    return openai_client, blob_service_client, azure_deployment, blob_container_name

@st.cache_data
def load_pdf_from_blob(_blob_service_client, container_name, _status=None, blob_name="AntBot_Manual.pdf"):
    """Blob Storage에서 PDF 다운로드 및 텍스트 추출"""
    try:
        if _status:
            _status.update(label="📦 Blob에서 PDF 다운로드 중...", state="running")
        
        # Blob 클라이언트 생성
        blob_client = _blob_service_client.get_blob_client(
            container=container_name, 
            blob=blob_name
        )
        
        # PDF 다운로드
        download_stream = blob_client.download_blob()
        pdf_data = download_stream.readall()
        if _status:
            _status.update(label=f"✅ PDF 다운로드 완료 ({len(pdf_data)/1024/1024:.1f} MB)", state="running")
        
        # PDF 텍스트 추출
        if _status:
            _status.update(label="📄 PDF 텍스트 추출 중... (시간이 걸릴 수 있습니다)", state="running")
        pdf_file = BytesIO(pdf_data)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text_content = ""
        total_pages = len(pdf_reader.pages)
        for i, page in enumerate(pdf_reader.pages):
            text_content += page.extract_text() + "\n"
            if _status and (i + 1) % 10 == 0:
                _status.update(label=f"📄 텍스트 추출 중... {i+1}/{total_pages} 페이지", state="running")
        
        if _status:
            _status.update(label=f"✅ 텍스트 추출 완료 ({total_pages}페이지)", state="running")
        
        # 텍스트 청킹 (간단한 방법)
        if _status:
            _status.update(label="✂️ 텍스트 청킹 중...", state="running")
        chunks = chunk_text(text_content)
        if _status:
            _status.update(label=f"✅ 청킹 완료 ({len(chunks)}개 청크)", state="complete")
        
        return chunks, text_content
    except Exception as e:
        if _status:
            _status.update(label=f"❌ 오류 발생", state="error")
        error_msg = str(e)
        print(f"❌ PDF 로딩 오류: {error_msg}")  # 터미널에 출력
        import traceback
        print(traceback.format_exc())  # 터미널에 전체 스택 추적 출력
        st.error(f"⚠️ PDF 로딩 중 오류: {error_msg}")
        st.error(f"📄 확인: {blob_name} 파일이 {container_name} 컨테이너에 존재하는지 확인하세요.")
        return [], ""

def chunk_text(text, chunk_size=1000, overlap=200):
    """텍스트를 청크로 분할"""
    # 문장 단위로 분할
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < chunk_size:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def find_relevant_context(query, chunks, top_k=3):
    """쿼리와 관련된 컨텍스트 찾기 (간단한 키워드 매칭)"""
    # 더 정교한 방법: Azure OpenAI Embeddings 사용
    # 여기서는 간단한 키워드 매칭 사용
    query_keywords = set(query.lower().split())
    
    chunk_scores = []
    for chunk in chunks:
        chunk_keywords = set(chunk.lower().split())
        score = len(query_keywords.intersection(chunk_keywords))
        chunk_scores.append((score, chunk))
    
    # 점수 기준 정렬 및 상위 k개 선택
    chunk_scores.sort(reverse=True, key=lambda x: x[0])
    relevant_chunks = [chunk for score, chunk in chunk_scores[:top_k] if score > 0]
    
    return relevant_chunks

def get_chatbot_response(openai_client, deployment, query, context_chunks):
    """Azure OpenAI를 사용하여 응답 생성"""
    
    # 컨텍스트 결합
    context = "\n\n".join(context_chunks) if context_chunks else "관련 문서를 찾을 수 없습니다."
    
    # 시스템 프롬프트
    system_message = """당신은 AntBot으로, 우리 팀의 솔루션 매뉴얼을 기반으로 질문에 답변하는 친절한 도우미입니다.
    
다음 규칙을 따라주세요:
1. 제공된 문서 컨텍스트를 기반으로 정확하게 답변하세요.
2. 문서에 없는 내용은 추측하지 말고, 모른다고 솔직히 말하세요.
3. 답변은 명확하고 이해하기 쉽게 작성하세요.
4. 필요한 경우 단계별로 설명하세요.
5. 한국어로 답변하세요."""

    user_message = f"""문서 컨텍스트:
{context}

사용자 질문: {query}

위 문서 컨텍스트를 참고하여 사용자 질문에 답변해주세요."""

    try:
        response = openai_client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"응답 생성 중 오류가 발생했습니다: {str(e)}"

# 메인 UI
def main():
    # 헤더
    st.markdown("""
        <div class="title-container">
            <h1>🤖 AntBot</h1>
            <p class="subtitle">팀 솔루션 매뉴얼 기반 AI 도우미</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 사이드바
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # 환경 변수 확인
        env_check = {
            "Azure OpenAI Endpoint": bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
            "Azure OpenAI API Key": bool(os.getenv("AZURE_OPENAI_API_KEY")),
            "Blob Connection String": bool(os.getenv("AZURE_BLOB_CONNECTION_STRING"))
        }
        
        st.subheader("연결 상태")
        for key, value in env_check.items():
            status = "✅" if value else "❌"
            st.text(f"{status} {key}")
        
        st.divider()
        
        # 디버그 정보
        if st.checkbox("🔍 디버그 정보 표시", value=False):
            st.subheader("디버그 정보")
            st.code(f"Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
            st.code(f"Deployment: {os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4')}")
            st.code(f"Container: {os.getenv('AZURE_BLOB_CONTAINER_NAME', 'antbot-docs')}")
        
        st.divider()
        
        st.subheader("📚 문서 정보")
        st.info("**매뉴얼:** antbot_manual.pdf")
        
        st.divider()
        
        if st.button("🗑️ 대화 초기화", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        st.divider()
        st.caption("Made with ❤️ for the team")
    
    # Azure 클라이언트 초기화
    try:
        openai_client, blob_service_client, deployment, container_name = init_azure_clients()
        
        # PDF 문서 로드
        status_placeholder = st.empty()
        with status_placeholder.status("📄 매뉴얼 로딩 중... 대용량 파일(294MB)이므로 시간이 걸릴 수 있습니다.", expanded=True) as status:
            chunks, full_text = load_pdf_from_blob(blob_service_client, container_name, _status=status)
        status_placeholder.empty()
        
        if not chunks:
            st.error("⚠️ 매뉴얼을 로드할 수 없습니다. Blob Storage 설정을 확인해주세요.")
            st.stop()
        
        # 세션 상태 초기화
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # 채팅 기록 표시
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # 사용자 입력
        if prompt := st.chat_input("무엇을 도와드릴까요?"):
            # 사용자 메시지 추가
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # 봇 응답 생성
            with st.chat_message("assistant"):
                with st.spinner("생각 중..."):
                    # 관련 컨텍스트 찾기
                    relevant_chunks = find_relevant_context(prompt, chunks)
                    
                    # 응답 생성
                    response = get_chatbot_response(
                        openai_client, 
                        deployment, 
                        prompt, 
                        relevant_chunks
                    )
                    
                    st.markdown(response)
            
            # 봇 메시지 추가
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        # 첫 방문 시 환영 메시지
        if len(st.session_state.messages) == 0:
            st.info("👋 안녕하세요! AntBot입니다. 팀 솔루션 매뉴얼에 대해 궁금한 점을 물어보세요!")
            
    except Exception as e:
        st.error(f"⚠️ 초기화 중 오류 발생: {str(e)}")
        st.info("💡 .env 파일 또는 환경 변수가 올바르게 설정되었는지 확인해주세요.")

if __name__ == "__main__":
    main()
