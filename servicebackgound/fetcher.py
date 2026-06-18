import logging
import re
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://normativa.udea.edu.co"
ENDPOINT = f"{BASE_URL}/Documentos/Consultar"

_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "accept-language": "es-ES,es;q=0.9,en;q=0.8",
    "content-type": "application/x-www-form-urlencoded",
    "origin": BASE_URL,
    "referer": ENDPOINT,
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),
}


@dataclass
class DocumentMeta:
    codigo: str  # ID interno para descargar el archivo
    numero: str  # numero visible en la tabla
    fecha: str  # fecha de expedicion
    vigencia: str  # entrada en vigencia
    resuelve: str  # descripcion del documento
    normas_relacionadas: str = ""
    download_url: str = field(init=False)

    def __post_init__(self) -> None:
        self.download_url = (
            f"{BASE_URL}/Documentos/Documento"
            f"?codigodocumento={self.codigo}&codigoimagen=&buscarpdf="
        )


def _build_payload(
    page: int,
    asunto: str = "",
    tipodocumento: str = "",
    dependencia: str = "",
) -> dict:
    return {
        "tipobusqueda": "indices",
        "restringido": "no",
        "ordenarpor": "indice2 DESC",
        "CurrentPage": str(page),
        "pdfini": "0",
        "pdffin": "0",
        "pdfcodigoinicial": "0",
        "buscartodo": "",
        "tipodocumento": tipodocumento,
        "dependencia": dependencia,
        "asunto": asunto,
        "fecha": "",
    }


def _extract_codigo(href: str) -> str:
    match = re.search(r"verdocumento\('(\d+)'", href)
    return match.group(1) if match else ""


def _parse_page(html: str) -> list[DocumentMeta]:
    soup = BeautifulSoup(html, "lxml")
    documents: list[DocumentMeta] = []

    for row in soup.select("table#tblresultados tr.documento"):
        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        link = cells[0].find("a")
        if not link:
            continue

        codigo = _extract_codigo(link.get("href", ""))
        if not codigo:
            continue

        documents.append(
            DocumentMeta(
                codigo=codigo,
                numero=link.get_text(strip=True),
                fecha=cells[1].get_text(strip=True),
                vigencia=cells[2].get_text(strip=True),
                resuelve=cells[4].get_text(strip=True),
                normas_relacionadas=cells[5].get_text(strip=True)
                if len(cells) > 5
                else "",
            )
        )

    return documents


def _has_next_page(html: str) -> bool:
    soup = BeautifulSoup(html, "lxml")
    pager = soup.select_one("div.pager")
    if not pager:
        return False
    # El ultimo elemento del pager es <a> si hay pagina siguiente,
    # <span class="disabled"> si ya es la ultima.
    children = [c for c in pager.children if getattr(c, "name", None) in ("a", "span")]
    last = children[-1] if children else None
    return last is not None and last.name == "a"


def fetch_documents(
    asunto: str = "",
    tipodocumento: str = "",
    dependencia: str = "",
) -> list[DocumentMeta]:
    documents: list[DocumentMeta] = []

    with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=30) as client:
        # GET inicial para establecer la cookie de sesion ASP.NET
        client.get(ENDPOINT)

        page = 1
        while True:
            logger.info("Fetching page %d ...", page)
            payload = _build_payload(page, asunto, tipodocumento, dependencia)
            response = client.post(ENDPOINT, data=payload)
            response.raise_for_status()

            page_docs = _parse_page(response.text)
            documents.extend(page_docs)
            logger.info("Page %d: %d documents found.", page, len(page_docs))

            if not _has_next_page(response.text):
                break

            page += 1

    logger.info("Total documents fetched: %d", len(documents))
    return documents


def download_pdf(codigo: str) -> bytes:
    """Descarga el PDF de un documento dado su codigo interno."""
    with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=30) as client:
        client.get(ENDPOINT)

        ext_resp = client.post(
            f"{BASE_URL}/Documentos/ExtensionDocumento",
            data={"codigodocumento": codigo},
        )
        ext_resp.raise_for_status()
        codigo_imagen = ext_resp.json()["codigoimagen"]

        download_url = (
            f"{BASE_URL}/Documentos/Documento"
            f"?codigodocumento={codigo}&codigoimagen={codigo_imagen}&buscarpdf="
        )
        response = client.get(download_url)
        response.raise_for_status()

    logger.info(
        "Downloaded PDF for codigo %s (%d bytes).", codigo, len(response.content)
    )
    return response.content
