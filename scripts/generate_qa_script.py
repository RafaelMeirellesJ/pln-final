
import os
import sys
import logging
from pathlib import Path

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load env vars
from dotenv import load_dotenv
load_dotenv()

from src.qa_generator import QAGenerator
from src.vector_store import QdrantVectorStore
from src.config import get_config

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    config = get_config()
    qa_gen = QAGenerator()
    vector_store = QdrantVectorStore()
    
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        logger.error("Uploads directory not found!")
        return

    files = list(uploads_dir.glob("*.md")) + list(uploads_dir.glob("*.pdf")) + list(uploads_dir.glob("*.txt"))
    
    logger.info(f"Found {len(files)} documents to process.")
    
    for file_path in files:
        logger.info(f"\n--- Processing: {file_path.name} ---")
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path.name}: {e}")
            continue
            
        # Generate QA Pairs
        params = {
            "num_questions": 20,
            "difficulty": "Intermediário",
            "temperature": 0.7,
            "questions_per_chunk": 20 # Try to get all in one go if possible, or handled by chunking
        }
        
        try:
            qa_content = qa_gen.generate_qa_pairs(content, params)
            if not qa_content:
                logger.warning(f"No QA content generated for {file_path.name}")
                continue
                
            # Convert to Documents
            # We create generic documents first
            documents = qa_gen.qa_to_documents(qa_content, "qa_collection")
            
            # Enrich metadata
            for doc in documents:
                doc.metadata['source_file'] = file_path.name
            
            logger.info(f"Generated {len(documents)} QA pairs.")
            
            # Insert into OpenAI Collection
            logger.info("Inserting into 'qa_compliance_openai'...")
            vector_store.insert_documents(
                collection_name="qa_compliance_openai",
                documents=documents,
                embedding_model="openai"
            )
            
            # Insert into Gemini Collection
            logger.info("Inserting into 'qa_compliance_gemini'...")
            vector_store.insert_documents(
                collection_name="qa_compliance_gemini",
                documents=documents,
                embedding_model="gemini"
            )
            
            logger.info(f"✅ Successfully processed {file_path.name}")
            
        except Exception as e:
            logger.error(f"❌ Error processing {file_path.name}: {e}")

if __name__ == "__main__":
    main()
