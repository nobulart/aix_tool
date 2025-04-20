import psutil
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def check_ram_usage():
    """Check current RAM usage and warn if exceeding threshold."""
    ram = psutil.virtual_memory()
    used_ram = ram.used / (1024 ** 3)  # Convert to GB
    total_ram = ram.total / (1024 ** 3)
    threshold = 50  # 50 GB threshold for a 64 GB system
    if used_ram > threshold:
        logger.warning("High RAM usage detected: %.2f GB used out of %.2f GB. Consider closing other applications.", used_ram, total_ram)
    return used_ram < threshold

def initial_model_check():
    """Prompt user to ensure LM Studio models are managed before starting."""
    logger.info("Please ensure LM Studio has the desired models loaded or unloaded to manage RAM usage.")
    logger.info("If you need to unload models, do so in the LM Studio UI (Model Manager > Unload All).")
    input("Press Enter to continue once models are managed...")