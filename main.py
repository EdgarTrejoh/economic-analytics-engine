import logging

from app.services.pipeline import run_pipeline


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


if __name__ == "__main__":
    run_pipeline()
