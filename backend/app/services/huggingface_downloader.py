import os
import logging
from typing import Optional
from huggingface_hub import hf_hub_download
from app.db.database import SessionLocal
from app.models.domain import LLMModel, ModelStatus
from app.core.config import MODELS_DIR

logger = logging.getLogger(__name__)

class HuggingFaceDownloader:
    def __init__(self):
        os.makedirs(MODELS_DIR, exist_ok=True)
        self._errors = {}  # model_id (str) -> error_message (str)

    def get_error(self, model_id) -> Optional[str]:
        import uuid
        return self._errors.get(str(model_id))

    def clear_error(self, model_id):
        self._errors.pop(str(model_id), None)

    def download_model(self, model_id: str):
        with SessionLocal() as db:
            model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
            if not model:
                logger.error(f"Model {model_id} not found for download.")
                return

            self.clear_error(model_id)
            model.status = ModelStatus.downloading
            db.commit()

            try:
                logger.info(f"Starting download for {model.name}...")
                local_path = hf_hub_download(
                    repo_id=model.hf_repo_id,
                    filename=model.gguf_filename,
                    local_dir=str(MODELS_DIR),
                    local_dir_use_symlinks=False
                )
                
                model.local_path = local_path
                model.status = ModelStatus.stopped
                db.commit()
                logger.info(f"Successfully downloaded {model.name} to {local_path}")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to download model {model.name}: {error_msg}")
                self._errors[str(model_id)] = error_msg
                model.status = ModelStatus.error
                db.commit()

downloader = HuggingFaceDownloader()
