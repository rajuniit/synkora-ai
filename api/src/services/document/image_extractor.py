"""Image extraction service for documents."""

import io
import logging
from typing import Any
from uuid import UUID

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from PIL import Image

from src.services.storage.s3_storage import S3StorageService

logger = logging.getLogger(__name__)


class ImageExtractor:
    """Extract images from documents (PDF, DOCX, HTML)."""

    def __init__(self, s3_service: S3StorageService):
        """
        Initialize image extractor.

        Args:
            s3_service: S3 storage service for uploading images
        """
        self.s3_service = s3_service

    async def extract_images_from_pdf(
        self, pdf_path: str, document_id: UUID, knowledge_base_id: int, min_width: int = 100, min_height: int = 100
    ) -> list[dict[str, Any]]:
        """
        Extract images from PDF file.

        Args:
            pdf_path: Path to PDF file (local or S3 URL)
            document_id: Document UUID
            knowledge_base_id: Knowledge base ID
            min_width: Minimum image width to extract
            min_height: Minimum image height to extract

        Returns:
            List of image metadata dictionaries
        """
        images = []

        try:
            # Download from S3 if it's an S3 URL
            if pdf_path.startswith("s3://") or pdf_path.startswith("https://"):
                logger.info(f"Downloading PDF from S3: {pdf_path}")
                pdf_data = await self.s3_service.download_file_content(pdf_path)
                pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
            else:
                pdf_doc = fitz.open(pdf_path)

            logger.info(f"Processing PDF with {len(pdf_doc)} pages")

            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                image_list = page.get_images()

                logger.info(f"Page {page_num + 1}: Found {len(image_list)} images")

                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = pdf_doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        # Open image to check dimensions
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        width, height = pil_image.size

                        # Skip small images (likely icons or decorations)
                        if width < min_width or height < min_height:
                            logger.debug(f"Skipping small image on page {page_num + 1}: {width}x{height}px")
                            continue

                        # Generate S3 key
                        image_filename = f"image_{page_num + 1}_{img_index + 1}.{image_ext}"
                        s3_key = (
                            f"knowledge-bases/kb-{knowledge_base_id}/"
                            f"documents/doc-{document_id}/images/{image_filename}"
                        )

                        # Upload to S3
                        logger.info(f"Uploading image to S3: {s3_key}")
                        s3_url = await self.s3_service.upload_file_content(
                            file_content=image_bytes, key=s3_key, content_type=f"image/{image_ext}"
                        )

                        # Store image metadata
                        images.append(
                            {
                                "page": page_num + 1,
                                "index": img_index + 1,
                                "filename": image_filename,
                                "s3_key": s3_key,
                                "s3_url": s3_url,
                                "width": width,
                                "height": height,
                                "format": image_ext.upper(),
                                "size_bytes": len(image_bytes),
                            }
                        )

                        logger.info(
                            f"✓ Extracted image {img_index + 1} from page {page_num + 1}: "
                            f"{width}x{height}px, {len(image_bytes)} bytes"
                        )

                    except Exception as e:
                        logger.error(f"Error extracting image {img_index + 1} from page {page_num + 1}: {e}")
                        continue

            pdf_doc.close()
            logger.info(f"✓ Extracted {len(images)} images from PDF")

        except Exception as e:
            logger.error(f"Error processing PDF: {e}", exc_info=True)

        return images

    async def extract_images_from_docx(
        self, docx_path: str, document_id: UUID, knowledge_base_id: int, min_width: int = 100, min_height: int = 100
    ) -> list[dict[str, Any]]:
        """
        Extract images from DOCX file.

        Args:
            docx_path: Path to DOCX file (local or S3 URL)
            document_id: Document UUID
            knowledge_base_id: Knowledge base ID
            min_width: Minimum image width to extract
            min_height: Minimum image height to extract

        Returns:
            List of image metadata dictionaries
        """
        images = []

        try:
            # Download from S3 if it's an S3 URL
            if docx_path.startswith("s3://") or docx_path.startswith("https://"):
                logger.info(f"Downloading DOCX from S3: {docx_path}")
                docx_data = await self.s3_service.download_file_content(docx_path)
                doc = DocxDocument(io.BytesIO(docx_data))
            else:
                doc = DocxDocument(docx_path)

            # Extract images from document relationships
            for _rel_id, rel in doc.part.rels.items():
                if "image" in rel.target_ref:
                    try:
                        image_part = rel.target_part
                        image_bytes = image_part.blob

                        # Open image to check dimensions and format
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        width, height = pil_image.size
                        image_format = pil_image.format.lower()

                        # Skip small images
                        if width < min_width or height < min_height:
                            logger.debug(f"Skipping small image: {width}x{height}px")
                            continue

                        # Generate S3 key
                        image_filename = f"image_{len(images) + 1}.{image_format}"
                        s3_key = (
                            f"knowledge-bases/kb-{knowledge_base_id}/"
                            f"documents/doc-{document_id}/images/{image_filename}"
                        )

                        # Upload to S3
                        logger.info(f"Uploading image to S3: {s3_key}")
                        s3_url = await self.s3_service.upload_file_content(
                            file_content=image_bytes, key=s3_key, content_type=f"image/{image_format}"
                        )

                        # Store image metadata
                        images.append(
                            {
                                "index": len(images) + 1,
                                "filename": image_filename,
                                "s3_key": s3_key,
                                "s3_url": s3_url,
                                "width": width,
                                "height": height,
                                "format": image_format.upper(),
                                "size_bytes": len(image_bytes),
                            }
                        )

                        logger.info(f"✓ Extracted image {len(images)}: {width}x{height}px, {len(image_bytes)} bytes")

                    except Exception as e:
                        logger.error(f"Error extracting image from DOCX: {e}")
                        continue

            logger.info(f"✓ Extracted {len(images)} images from DOCX")

        except Exception as e:
            logger.error(f"Error processing DOCX: {e}", exc_info=True)

        return images

    async def extract_images_from_html(
        self, html_content: str, document_id: UUID, knowledge_base_id: int, base_url: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Extract images from HTML content.

        Note: This extracts image URLs from HTML. For embedded base64 images,
        additional processing would be needed.

        Args:
            html_content: HTML content string
            document_id: Document UUID
            knowledge_base_id: Knowledge base ID
            base_url: Base URL for resolving relative image URLs

        Returns:
            List of image metadata dictionaries
        """
        images = []

        try:
            from urllib.parse import urljoin

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")
            img_tags = soup.find_all("img")

            logger.info(f"Found {len(img_tags)} img tags in HTML")

            for idx, img_tag in enumerate(img_tags):
                try:
                    src = img_tag.get("src")
                    if not src:
                        continue

                    # Handle base64 embedded images
                    if src.startswith("data:image"):
                        logger.debug(f"Skipping base64 embedded image {idx + 1}")
                        # Base64 images are skipped - add extraction if needed
                        continue

                    # Resolve relative URLs
                    if base_url and not src.startswith(("http://", "https://")):
                        src = urljoin(base_url, src)

                    # Store image reference
                    images.append(
                        {
                            "index": idx + 1,
                            "url": src,
                            "alt": img_tag.get("alt", ""),
                            "title": img_tag.get("title", ""),
                            "width": img_tag.get("width"),
                            "height": img_tag.get("height"),
                        }
                    )

                except Exception as e:
                    logger.error(f"Error processing img tag {idx + 1}: {e}")
                    continue

            logger.info(f"✓ Extracted {len(images)} image references from HTML")

        except Exception as e:
            logger.error(f"Error processing HTML: {e}", exc_info=True)

        return images

    async def extract_images(
        self, file_path: str, file_type: str, document_id: UUID, knowledge_base_id: int, **kwargs
    ) -> list[dict[str, Any]]:
        """
        Extract images from document based on file type.

        Args:
            file_path: Path to file (local or S3 URL)
            file_type: File type (pdf, docx, html)
            document_id: Document UUID
            knowledge_base_id: Knowledge base ID
            **kwargs: Additional arguments for specific extractors

        Returns:
            List of image metadata dictionaries
        """
        file_type = file_type.lower()

        if file_type == "pdf":
            return await self.extract_images_from_pdf(file_path, document_id, knowledge_base_id, **kwargs)
        elif file_type in ["docx", "doc"]:
            return await self.extract_images_from_docx(file_path, document_id, knowledge_base_id, **kwargs)
        elif file_type in ["html", "htm"]:
            return await self.extract_images_from_html(
                kwargs.get("html_content", ""), document_id, knowledge_base_id, kwargs.get("base_url")
            )
        else:
            logger.warning(f"Unsupported file type for image extraction: {file_type}")
            return []
