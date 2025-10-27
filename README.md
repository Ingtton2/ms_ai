# 🤖 AntBot - 팀 솔루션 챗봇

Azure OpenAI와 Blob Storage를 활용한 팀 솔루션 매뉴얼 기반 AI 챗봇입니다.

## ✨ 주요 기능

- 📄 Azure Blob Storage에서 PDF 매뉴얼 자동 로드
- 🤖 Azure OpenAI GPT 모델을 활용한 자연어 질의응답
- 💬 깔끔한 Streamlit 채팅 인터페이스
- 🔍 문서 기반 컨텍스트 검색 및 답변 생성
- 💾 대화 기록 저장

## 📋 사전 요구사항

1. **Azure OpenAI 리소스**
   - Azure Portal에서 OpenAI 리소스 생성
   - GPT-4 또는 GPT-3.5-turbo 모델 배포
   - API Key 및 Endpoint 확보

2. **Azure Storage Account**
   - Blob Storage 컨테이너 생성 (예: `antbot-docs`)
   - Connection String 확보
   - `antbot_manual.pdf` 파일 업로드

3. **Python 3.8 이상**

## 🚀 설치 및 설정

### 1. 저장소 클론 및 의존성 설치

```bash
# 의존성 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 실제 값으로 수정:

```bash
cp .env.example .env
```

`.env` 파일 내용:

```env
# Azure OpenAI 설정
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure Blob Storage 설정
AZURE_BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=your-account-name;AccountKey=your-account-key;EndpointSuffix=core.windows.net
AZURE_BLOB_CONTAINER_NAME=antbot-docs
```

### 3. Azure Blob Storage에 PDF 업로드

#### Azure Portal에서 업로드:
1. Azure Portal → Storage Account → Containers
2. `antbot-docs` 컨테이너 선택 (없으면 생성)
3. "Upload" 버튼 클릭
4. `antbot_manual.pdf` 파일 선택 및 업로드

#### Azure CLI로 업로드:
```bash
az storage blob upload \
  --account-name your-account-name \
  --container-name antbot-docs \
  --name antbot_manual.pdf \
  --file ./antbot_manual.pdf \
  --connection-string "your-connection-string"
```

#### Python으로 업로드:
```python
from azure.storage.blob import BlobServiceClient

# Connection String으로 클라이언트 생성
blob_service_client = BlobServiceClient.from_connection_string("your-connection-string")
blob_client = blob_service_client.get_blob_client(container="antbot-docs", blob="antbot_manual.pdf")

# 파일 업로드
with open("antbot_manual.pdf", "rb") as data:
    blob_client.upload_blob(data, overwrite=True)
print("✅ 파일 업로드 완료!")
```

## 🎮 실행 방법

```bash
streamlit run app.py
```

브라우저에서 자동으로 열리며, 일반적으로 `http://localhost:8501`에서 접근 가능합니다.

## 📱 사용 방법

1. **애플리케이션 시작**: 위 실행 명령으로 앱 시작
2. **사이드바 확인**: 모든 설정이 ✅로 표시되는지 확인
3. **질문 입력**: 하단 채팅 입력창에 질문 입력
4. **답변 받기**: AntBot이 매뉴얼 기반으로 답변 생성

### 예시 질문

- "이 솔루션의 주요 기능은 무엇인가요?"
- "설치 방법을 알려주세요"
- "문제 해결 방법은 어떻게 되나요?"
- "사용자 권한 설정은 어떻게 하나요?"

## 🛠️ 구조 및 작동 원리

### 파일 구조
```
antbot/
├── app.py                 # 메인 Streamlit 애플리케이션
├── requirements.txt       # Python 의존성
├── .env                  # 환경 변수 (비공개)
├── .env.example          # 환경 변수 템플릿
└── README.md             # 이 파일
```

### 작동 흐름

1. **문서 로드**: Azure Blob Storage에서 `antbot_manual.pdf` 다운로드
2. **텍스트 추출**: PyPDF2로 PDF 내용 추출
3. **청킹**: 문서를 작은 청크로 분할 (검색 최적화)
4. **사용자 질문**: Streamlit 채팅 인터페이스에서 질문 입력
5. **컨텍스트 검색**: 질문과 관련된 문서 청크 찾기
6. **답변 생성**: Azure OpenAI에 컨텍스트와 질문 전달하여 답변 생성
7. **결과 표시**: 채팅 인터페이스에 답변 표시

## 🔧 고급 설정

### 검색 품질 향상

더 정교한 검색을 원하면 Azure OpenAI Embeddings 사용을 권장합니다:

```python
# app.py의 find_relevant_context 함수를 다음으로 대체:

def get_embeddings(text, openai_client):
    """텍스트 임베딩 생성"""
    response = openai_client.embeddings.create(
        model="text-embedding-ada-002",  # 또는 사용 중인 임베딩 모델
        input=text
    )
    return response.data[0].embedding

def find_relevant_context_with_embeddings(query, chunks, openai_client, top_k=3):
    """임베딩 기반 컨텍스트 검색"""
    import numpy as np
    
    query_embedding = get_embeddings(query, openai_client)
    
    chunk_similarities = []
    for chunk in chunks:
        chunk_embedding = get_embeddings(chunk, openai_client)
        # 코사인 유사도 계산
        similarity = np.dot(query_embedding, chunk_embedding)
        chunk_similarities.append((similarity, chunk))
    
    chunk_similarities.sort(reverse=True, key=lambda x: x[0])
    return [chunk for _, chunk in chunk_similarities[:top_k]]
```

### 배포 옵션

#### Streamlit Cloud
1. GitHub 저장소에 코드 푸시
2. [streamlit.io/cloud](https://streamlit.io/cloud) 방문
3. "New app" 클릭 및 저장소 연결
4. Secrets에 환경 변수 설정

#### Azure App Service
```bash
az webapp up --name antbot --resource-group your-rg --runtime "PYTHON:3.11"
```

## 🐛 문제 해결

### 연결 오류
- `.env` 파일의 모든 설정이 올바른지 확인
- Azure Portal에서 API Key와 Endpoint 재확인
- Blob Storage Connection String 확인

### PDF 로딩 실패
- Blob Storage에 `antbot_manual.pdf` 파일이 존재하는지 확인
- 컨테이너 이름이 `.env`의 설정과 일치하는지 확인
- Storage Account 접근 권한 확인

### 응답 생성 실패
- Azure OpenAI 배포 이름 확인
- API 버전 호환성 확인
- 할당량 및 사용량 제한 확인

## 📝 라이선스

팀 내부용 솔루션

## 🤝 기여

팀원 누구나 개선 사항을 제안할 수 있습니다!

## 📧 문의

문제가 있거나 개선 사항이 있으면 팀 채널로 문의해주세요.

---

**Made with ❤️ for the team**
