"""
Azure Blob Storage에 PDF 파일을 업로드하는 헬퍼 스크립트
"""

import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

def upload_pdf_to_blob(file_path, blob_name=None):
    """
    PDF 파일을 Azure Blob Storage에 업로드
    
    Args:
        file_path (str): 업로드할 PDF 파일 경로
        blob_name (str, optional): Blob Storage에 저장될 파일명. 기본값은 원본 파일명
    """
    
    # 환경 변수에서 설정 가져오기
    connection_string = os.getenv("AZURE_BLOB_CONNECTION_STRING")
    container_name = os.getenv("AZURE_BLOB_CONTAINER_NAME", "antbot-docs")
    
    if not connection_string:
        print("❌ AZURE_BLOB_CONNECTION_STRING 환경 변수가 설정되지 않았습니다.")
        print("💡 .env 파일을 확인해주세요.")
        return False
    
    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return False
    
    # Blob 이름 설정
    if blob_name is None:
        blob_name = os.path.basename(file_path)
    
    try:
        print(f"🔄 Azure Blob Storage에 연결 중...")
        
        # Blob Service Client 생성
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # 컨테이너가 없으면 생성
        try:
            container_client = blob_service_client.get_container_client(container_name)
            if not container_client.exists():
                print(f"📦 컨테이너 '{container_name}' 생성 중...")
                blob_service_client.create_container(container_name)
        except Exception as e:
            print(f"⚠️ 컨테이너 확인 중 오류: {str(e)}")
        
        # Blob Client 생성
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        print(f"📤 파일 업로드 중: {file_path} → {blob_name}")
        
        # 파일 업로드
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        
        print(f"✅ 업로드 완료!")
        print(f"📍 위치: 컨테이너 '{container_name}' / 파일 '{blob_name}'")
        
        # 파일 정보 표시
        blob_properties = blob_client.get_blob_properties()
        file_size_mb = blob_properties.size / (1024 * 1024)
        print(f"📊 파일 크기: {file_size_mb:.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ 업로드 중 오류 발생: {str(e)}")
        return False

def list_blobs_in_container():
    """컨테이너의 모든 blob 목록 출력"""
    
    connection_string = os.getenv("AZURE_BLOB_CONNECTION_STRING")
    container_name = os.getenv("AZURE_BLOB_CONTAINER_NAME", "antbot-docs")
    
    if not connection_string:
        print("❌ AZURE_BLOB_CONNECTION_STRING 환경 변수가 설정되지 않았습니다.")
        return
    
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        print(f"\n📂 컨테이너 '{container_name}'의 파일 목록:")
        print("-" * 60)
        
        blob_list = container_client.list_blobs()
        
        count = 0
        for blob in blob_list:
            count += 1
            size_mb = blob.size / (1024 * 1024)
            print(f"{count}. {blob.name} ({size_mb:.2f} MB)")
        
        if count == 0:
            print("(파일 없음)")
        else:
            print("-" * 60)
            print(f"총 {count}개 파일")
        
    except Exception as e:
        print(f"❌ 목록 조회 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 AntBot - Azure Blob Storage 업로드 도구")
    print("=" * 60)
    print()
    
    # 파일 경로 입력
    default_file = "antbot_manual.pdf"
    file_path = input(f"업로드할 PDF 파일 경로 (기본: {default_file}): ").strip()
    
    if not file_path:
        file_path = default_file
    
    # 업로드 실행
    success = upload_pdf_to_blob(file_path)
    
    if success:
        print()
        # 업로드 후 목록 확인
        list_blobs_in_container()
        print()
        print("🎉 모든 작업이 완료되었습니다!")
        print("💡 이제 'streamlit run app.py'로 챗봇을 실행할 수 있습니다.")
    else:
        print()
        print("⚠️ 업로드에 실패했습니다. 설정을 확인해주세요.")
