import urllib.request
import time
import logging

logger = logging.getLogger(__name__)

def download_dataset(dataset_urls, output_path, retries=3, delay=2):
    """Download a public dataset with retries and fallback URLs."""
    for url in dataset_urls:
        for attempt in range(retries):
            try:
                urllib.request.urlretrieve(url, output_path)
                logger.info("Downloaded dataset to %s from %s", output_path, url)
                return True
            except urllib.error.HTTPError as e:
                logger.warning("Attempt %d/%d failed to download dataset from %s: %s", attempt + 1, retries, url, e)
                if attempt < retries - 1:
                    time.sleep(delay)
            except Exception as e:
                logger.error("Failed to download dataset from %s: %s", url, e)
                break
    logger.warning("All dataset download attempts failed. Continuing without dataset.")
    return False