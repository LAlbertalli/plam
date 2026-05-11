import psutil
import logging

logger = logging.getLogger(__name__)

# Minimum free RAM required to be left available (10 GB)
MIN_FREE_RAM_MB = 10240

class ResourceManager:
    @staticmethod
    def get_system_metrics():
        vm = psutil.virtual_memory()
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_total_mb": vm.total / (1024 * 1024),
            "ram_used_mb": vm.used / (1024 * 1024),
            "ram_free_mb": vm.available / (1024 * 1024)
        }

    @staticmethod
    def can_allocate(ram_required_mb: int) -> bool:
        vm = psutil.virtual_memory()
        free_mb = vm.available / (1024 * 1024)
        if (free_mb - ram_required_mb) >= MIN_FREE_RAM_MB:
            return True
        return False

resource_manager = ResourceManager()
