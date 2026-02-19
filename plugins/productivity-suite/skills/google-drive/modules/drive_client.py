#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-api-python-client>=2.100.0",
#     "google-auth-oauthlib>=1.1.0",
#     "google-auth>=2.23.0",
# ]
# ///
"""
Google Drive Client Module

Provides a unified interface for Google Drive operations across multiple profiles.
"""

import sys
from pathlib import Path
from typing import Optional, Callable

SKILL_DIR = Path(__file__).parent.parent
INTEGRATIONS_DIR = SKILL_DIR.parent.parent / 'integrations/google/scripts'
sys.path.insert(0, str(INTEGRATIONS_DIR))

from google_auth import get_credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import io


class DriveClient:
    """Google Drive API client with multi-profile support."""

    # Common MIME types
    MIME_FOLDER = 'application/vnd.google-apps.folder'
    MIME PDF = 'application/pdf'

    def __init__(self, profile: str = 'default', readonly: bool = False):
        """Initialize Drive client.

        Args:
            profile: Account profile ('default' for business, 'youtube' for personal, etc.)
            readonly: If True, use read-only scope
        """
        self.profile = profile
        scopes = ['drive.readonly'] if readonly else ['drive']
        self.credentials = get_credentials(scopes, profile=profile)
        self.service = build('drive', 'v3', credentials=self.credentials)

    def search(self, query: str, fields: str = None, page_size: int = 100) -> list[dict]:
        """Search for files matching query.

        Args:
            query: Drive search query (see https://developers.google.com/drive/api/guides/search-files)
            fields: Fields to return (default: files(id,name,mimeType,webViewLink,modifiedTime))
            page_size: Number of results per page

        Returns:
            List of file dicts
        """
        if fields is None:
            fields = 'files(id,name,mimeType,webViewLink,modifiedTime,parents,size,md5Checksum)'

        results = []
        page_token = None

        try:
            while True:
                response = self.service.files().list(
                    q=query,
                    fields=f'nextPageToken,{fields}',
                    pageSize=page_size,
                    pageToken=page_token,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True
                ).execute()

                results.extend(response.get('files', []))
                page_token = response.get('nextPageToken')

                if not page_token:
                    break

            return results

        except HttpError as e:
            raise RuntimeError(f"Search failed: {e}") from e

    def get_file(self, file_id: str, fields: str = None) -> dict:
        """Get file metadata by ID.

        Args:
            file_id: Drive file ID
            fields: Fields to return

        Returns:
            File metadata dict
        """
        if fields is None:
            fields = 'id,name,mimeType,webViewLink,modifiedTime,parents,size,md5Checksum'

        try:
            return self.service.files().get(
                fileId=file_id,
                fields=fields,
                supportsAllDrives=True
            ).execute()
        except HttpError as e:
            raise RuntimeError(f"Failed to get file {file_id}: {e}") from e

    def upload(
        self,
        file_path: str,
        name: Optional[str] = None,
        folder_id: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> dict:
        """Upload a file (standard upload for small/medium files).

        Args:
            file_path: Path to file to upload
            name: Custom filename (defaults to original filename)
            folder_id: Parent folder ID (defaults to root)
            mime_type: MIME type (auto-detected if None)

        Returns:
            Created file metadata
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        metadata = {'name': name or file_path.name}
        if folder_id:
            metadata['parents'] = [folder_id]

        media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=False)

        try:
            file = self.service.files().create(
                body=metadata,
                media_body=media,
                fields='id,name,mimeType,webViewLink,md5Checksum,size',
                supportsAllDrives=True
            ).execute()
            return file
        except HttpError as e:
            raise RuntimeError(f"Upload failed: {e}") from e

    def upload_large(
        self,
        file_path: str,
        name: Optional[str] = None,
        folder_id: Optional[str] = None,
        chunksize: int = 1024 * 1024,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> dict:
        """Upload a large file with resumable upload and progress tracking.

        Args:
            file_path: Path to file to upload
            name: Custom filename (defaults to original filename)
            folder_id: Parent folder ID (defaults to root)
            chunksize: Upload chunk size in bytes (default: 1MB)
            progress_callback: Optional callback(int) for progress updates (0-100)

        Returns:
            Created file metadata
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size
        metadata = {'name': name or file_path.name}
        if folder_id:
            metadata['parents'] = [folder_id]

        media = MediaFileUpload(
            str(file_path),
            chunksize=chunksize,
            resumable=True
        )

        try:
            request = self.service.files().create(
                body=metadata,
                media_body=media,
                fields='id,name,mimeType,webViewLink,md5Checksum,size',
                supportsAllDrives=True
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    if progress_callback:
                        progress_callback(progress)

            return response

        except HttpError as e:
            raise RuntimeError(f"Large upload failed: {e}") from e

    def create_folder(self, name: str, parent_id: Optional[str] = None) -> dict:
        """Create a folder.

        Args:
            name: Folder name
            parent_id: Parent folder ID (defaults to root)

        Returns:
            Created folder metadata
        """
        metadata = {
            'name': name,
            'mimeType': self.MIME_FOLDER
        }
        if parent_id:
            metadata['parents'] = [parent_id]

        try:
            folder = self.service.files().create(
                body=metadata,
                fields='id,name,mimeType,webViewLink',
                supportsAllDrives=True
            ).execute()
            return folder
        except HttpError as e:
            raise RuntimeError(f"Failed to create folder: {e}") from e

    def list_folder(self, folder_id: str = 'root', fields: str = None) -> list[dict]:
        """List contents of a folder.

        Args:
            folder_id: Folder ID (use 'root' for root folder)
            fields: Fields to return

        Returns:
            List of file/folder dicts
        """
        if fields is None:
            fields = 'files(id,name,mimeType,webViewLink,modifiedTime,size)'

        query = f"'{folder_id}' in parents and trashed=false"

        try:
            response = self.service.files().list(
                q=query,
                fields=fields,
                pageSize=100,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True
            ).execute()
            return response.get('files', [])
        except HttpError as e:
            raise RuntimeError(f"Failed to list folder {folder_id}: {e}") from e

    def download(self, file_id: str, output_path: str) -> dict:
        """Download a file.

        Args:
            file_id: Drive file ID
            output_path: Local file path to save to

        Returns:
            File metadata
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Get file metadata
            file = self.get_file(file_id, fields='id,name,mimeType')

            # For Google Docs/Sheets/Slides, export to appropriate format
            if file['mimeType'].startswith('application/vnd.google-apps'):
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimetype=self._get_export_mime_type(file['mimeType'])
                )
            else:
                request = self.service.files().get_media(fileId=file_id)

            with io.FileIO(output_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()

            return file

        except HttpError as e:
            raise RuntimeError(f"Download failed: {e}") from e

    def _get_export_mime_type(self, google_mime_type: str) -> str:
        """Get export MIME type for Google Docs files."""
        export_map = {
            'application/vnd.google-apps.document': 'application/pdf',
            'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.google-apps.drawing': 'image/png',
        }
        return export_map.get(google_mime_type, 'application/pdf')

    def find_folder_by_name(self, name: str, parent_id: Optional[str] = None) -> Optional[dict]:
        """Find a folder by name.

        Args:
            name: Folder name to search for
            parent_id: Limit search to this parent folder

        Returns:
            Folder dict if found, None otherwise
        """
        query = f"mimeType='{self.MIME_FOLDER}' and name='{name}' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = self.search(query, fields='files(id,name,mimeType,webViewLink,parents)')
        return results[0] if results else None

    def get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> dict:
        """Get existing folder or create new one.

        Args:
            name: Folder name
            parent_id: Parent folder ID

        Returns:
            Folder metadata (existing or newly created)
        """
        existing = self.find_folder_by_name(name, parent_id)
        if existing:
            return existing
        return self.create_folder(name, parent_id)


if __name__ == '__main__':
    # Test connection
    client = DriveClient(profile='default')
    print(f"Connected to Drive (profile: {client.profile})")

    # Test search
    files = client.search("name contains 'test'", page_size=5)
    print(f"Found {len(files)} files")
