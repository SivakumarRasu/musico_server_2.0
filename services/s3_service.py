import os
import re
import uuid
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, BotoCoreError

load_dotenv()
logger = logging.getLogger("uvicorn.error")


class S3Service:
    def __init__(self):
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        self.region = os.getenv("AWS_REGION", "ap-south-2")
        self.bucket = os.getenv("AWS_S3_BUCKET", "")
        self.custom_domain = os.getenv("AWS_S3_CUSTOM_DOMAIN") or None

    
    def get_s3_status(self) -> Dict[str, Any]:
        """Returns the current configuration status of S3."""
        is_configured = bool(self.access_key and self.secret_key and self.bucket)
        return {
            "is_configured": is_configured,
            "bucket": self.bucket or None,
            "region": self.region,
            "custom_domain": self.custom_domain or None,
            "has_access_key": bool(self.access_key),
            "has_secret_key": bool(self.secret_key),
        }

    def _get_client(self):
        
        if not (self.access_key and self.secret_key):
            raise ValueError("AWS credentials (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY) are not configured.")
        if not self.bucket:
            raise ValueError("AWS_S3_BUCKET is not configured.")

        return boto3.client(
            "s3",
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    def generate_presigned_upload_url(
        self,
        filename: str,
        content_type: str = "application/vnd.android.package-archive",
        folder: str = "releases",
        expires_in: int = 3600
    ) -> Dict[str, Any]:
        """
        Generates a pre-signed PUT URL allowing clients to upload directly to S3.
        """
        client = self._get_client()

        # Sanitize filename
        clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename or "release.apk")
        key = f"{folder.strip('/')}/{uuid.uuid4().hex[:8]}_{clean_name}"

        try:
            presigned_url = client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )

            # Public download URL
            if self.custom_domain:
                download_url = f"https://{self.custom_domain.rstrip('/')}/{key}"
            else:
                download_url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"

            return {
                "upload_url": presigned_url,
                "download_url": download_url,
                "s3_key": key,
                "bucket": self.bucket,
                "region": self.region,
                "expires_in": expires_in,
            }
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to generate S3 pre-signed URL: {e}")
            raise RuntimeError(f"AWS S3 Error: {str(e)}")

    def upload_file_direct(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "application/vnd.android.package-archive",
        folder: str = "releases"
    ) -> Dict[str, Any]:
        """
        Server-side direct upload fallback (useful if browser S3 CORS is not configured).
        """
        client = self._get_client()
        clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename or "release.apk")
        key = f"{folder.strip('/')}/{uuid.uuid4().hex[:8]}_{clean_name}"

        try:
            client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_bytes,
                ContentType=content_type,
            )

            if self.custom_domain:
                download_url = f"https://{self.custom_domain.rstrip('/')}/{key}"
            else:
                download_url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"

            return {
                "download_url": download_url,
                "s3_key": key,
                "bucket": self.bucket,
                "file_size": len(file_bytes),
            }
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to upload directly to S3: {e}")
            raise RuntimeError(f"AWS S3 Direct Upload Error: {str(e)}")
