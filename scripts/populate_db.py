import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.documents import Document

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import get_config
from src.vector_store import QdrantVectorStore
from src.document_processor import DocumentProcessor
from src.storage import StorageManager

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    load_dotenv()
    vector_store = QdrantVectorStore()
    doc_processor = DocumentProcessor()
    storage_manager = StorageManager()
    
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        logger.error(f"❌ Diretório {uploads_dir} não encontrado!")
        return

    # ==========================================
    # 1. DEFINIÇÃO DAS COLLECTIONS
    # ==========================================
    
    # Collections de Documentos (Processamento de PDF/MD)
    doc_collections = [
        {"name": "compliance_openai", "model": "openai", "desc": "Documentos de Compliance (OpenAI)"},
        {"name": "compliance_gemini", "model": "gemini", "desc": "Documentos de Compliance (Gemini)"}
    ]
    
    # Collections de QA (Importação de JSON)
    qa_collections = [
        {"name": "qa_compliance_openai", "model": "openai", "desc": "QA Pairs (OpenAI)"},
        {"name": "qa_compliance_gemini", "model": "gemini", "desc": "QA Pairs (Gemini)"}
    ]

    all_collections = doc_collections + qa_collections

    logger.info("🚀 Iniciando script unificado de população de banco de dados...")

    # ==========================================
    # 2. CRIAÇÃO DAS COLLECTIONS
    # ==========================================
    logger.info("\n--- 1. Verificando/Criando Collections ---")
    for col in all_collections:
        try:
            vector_store.create_collection(col["name"], col["model"], col["desc"])
            logger.info(f"✅ Collection '{col['name']}' pronta.")
        except Exception as e:
            logger.info(f"ℹ️ Collection '{col['name']}' status: {e}")

    # ==========================================
    # 3. PROCESSAMENTO DE DOCUMENTOS (PDF/MD/TXT)
    # ==========================================
    logger.info("\n--- 2. Processando Documentos (PDF/MD/TXT) ---")
    files = list(uploads_dir.glob("*.md")) + list(uploads_dir.glob("*.pdf")) + list(uploads_dir.glob("*.txt"))
    
    if not files:
        logger.warning("⚠️ Nenhum arquivo de documento encontrado em 'uploads/'.")
    else:
        for file_path in files:
            logger.info(f"\n📄 Processando: {file_path.name}")
            try:
                # Processar documento
                processed_data = doc_processor.process_document(str(file_path), enhance=False)
                documents = processed_data["chunks"]
                
                if not documents:
                    logger.warning(f"⚠️ Nenhum chunk gerado para {file_path.name}")
                    continue

                # Inserir nas collections de Documentos
                for col in doc_collections:
                    logger.info(f"  ↳ Enviando para '{col['name']}'...")
                    
                    # Upload MinIO
                    try:
                        upload_result = storage_manager.upload_document(str(file_path), topic=col["name"])
                        minio_path = upload_result['object_name']
                    except Exception as e:
                        logger.error(f"    ❌ Falha no upload MinIO: {e}")
                        minio_path = ""

                    # Atualizar metadata
                    for chunk in documents:
                        chunk.metadata['minio_path'] = minio_path
                        chunk.metadata['collection_name'] = col["name"]

                    # Inserir Qdrant
                    try:
                        vector_store.insert_documents(col["name"], documents, col["model"])
                        logger.info(f"    ✅ Sucesso: {len(documents)} chunks inseridos.")
                    except Exception as e:
                        logger.error(f"    ❌ Falha na inserção: {e}")

            except Exception as e:
                logger.error(f"❌ Erro ao processar {file_path.name}: {e}")

    # ==========================================
    # 4. IMPORTAÇÃO DE QA (JSON)
    # ==========================================
    logger.info("\n--- 3. Importando Dataset de QA (JSON) ---")
    qa_dataset_path = uploads_dir / "qa_dataset.json"
    
    if qa_dataset_path.exists():
        try:
            with open(qa_dataset_path, 'r', encoding='utf-8') as f:
                qa_data = json.load(f)
                
            if qa_data:
                # Converter para Documents
                qa_documents = []
                for item in qa_data:
                    doc = Document(page_content=item['content'], metadata=item.get('metadata', {}))
                    qa_documents.append(doc)
                
                logger.info(f"📦 Carregados {len(qa_documents)} pares de QA do JSON.")
                
                # Inserir nas collections de QA
                for col in qa_collections:
                    logger.info(f"  ↳ Enviando para '{col['name']}'...")
                    try:
                        vector_store.insert_documents(col["name"], qa_documents, col["model"])
                        logger.info(f"    ✅ Sucesso: QA importado.")
                    except Exception as e:
                        logger.error(f"    ❌ Falha na importação: {e}")
            else:
                logger.warning("⚠️ O arquivo qa_dataset.json está vazio.")
        except Exception as e:
            logger.error(f"❌ Erro ao ler qa_dataset.json: {e}")
    else:
        logger.warning("⚠️ Arquivo 'qa_dataset.json' não encontrado. Pule este passo se não tiver dados de QA.")

    logger.info("\n🎉 Processo Unificado Concluído! Todas as collections foram atualizadas.")

if __name__ == "__main__":
    main()
