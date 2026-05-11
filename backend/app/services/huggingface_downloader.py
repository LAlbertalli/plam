import os
import logging
from huggingface_hub import hf_hub_download
from app.db.database import SessionLocal
from app.models.domain import LLMModel, ModelStatus

logger = logging.getLogger(__name__)

MODELS_DIR = "/home/luca/plam/data/models"

class HuggingFaceDownloader:
    def __init__(self):
        os.makedirs(MODELS_DIR, exist_ok=True)

    def download_model(self, model_id: str):
        with SessionLocal() as db:
            model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
            if not model:
                logger.error(f"Model {model_id} not found for download.")
                return

            model.status = ModelStatus.downloading
            db.commit()

            try:
                logger.info(f"Starting download for {model.name}...")
                local_path = hf_hub_download(
                    repo_id=model.hf_repo_id,
                    filename=model.gguf_filename,
                    local_dir=MODELS_DIR,
                    local_dir_use_symlinks=False
                )
                
                model.local_path = local_path
                model.status = ModelStatus.stopped
                db.commit()
                logger.info(f"Successfully downloaded {model.name} to {local_path}")
                
            except Exception as e:
                logger.error(f"Failed to download model {model.name}: {e}")
                model.status = ModelStatus.error
                db.commit()

downloader = HuggingFaceDownloader()
