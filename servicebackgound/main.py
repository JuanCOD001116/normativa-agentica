import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from servicebackgound.embedder import embed_and_store
from servicebackgound.fetcher import download_pdf, fetch_documents
from servicebackgound.storage import list_existing, upload_pdf

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# "debug"     → corre inmediatamente y sale
# "scheduled" → cron diario (default produccion)
RUN_MODE = os.getenv("SERVICE_RUN_MODE", "scheduled")

# Expresion cron estandar: minuto hora dia mes dia_semana
# Ejemplo: "0 1 * * *" → todos los dias a la 1:00 AM
CRON_EXPRESSION = os.getenv("SERVICE_CRON_EXPRESSION", "0 1 * * *")


def run_ingestion() -> None:
    logger.info("Ingestion pipeline started.")

    documents = fetch_documents(asunto="ESTATUTO DEL PROFESOR DE CATEDRA Y OCASIONAL")
    logger.info("Step 1 complete — %d documents retrieved.", len(documents))

    existing = list_existing()
    new_documents = [doc for doc in documents if doc.codigo not in existing]
    logger.info(
        "%d already in bucket, %d new to process.",
        len(existing),
        len(new_documents),
    )

    if not new_documents:
        logger.info("Nothing to do. Ingestion finished.")
        return

    for doc in new_documents:
        pdf_bytes = download_pdf(doc.codigo)
        upload_pdf(doc.codigo, pdf_bytes)
        embed_and_store(
            pdf_bytes,
            metadata={
                "codigo": doc.codigo,
                "numero": doc.numero,
                "fecha": doc.fecha,
                "resuelve": doc.resuelve,
            },
        )
    logger.info("Step 2 & 3 complete — %d new PDFs procesados.", len(new_documents))

    logger.info("Ingestion pipeline finished.")


def main() -> None:
    if RUN_MODE == "debug":
        logger.info("Running in debug mode — executing ingestion immediately.")
        run_ingestion()
        return

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_ingestion,
        CronTrigger.from_crontab(CRON_EXPRESSION),
        id="daily_ingestion",
        replace_existing=True,
    )
    logger.info("Scheduler started. Cron expression: %s", CRON_EXPRESSION)
    scheduler.start()


if __name__ == "__main__":
    main()
