#!/usr/bin/env python3
"""
1Password to CSV Converter

This script converts exported 1Password (.1pux) files to CSV format
for import into other password managers.
"""

import argparse
import csv
import json
import logging
import shutil
import sys
import tempfile
import zipfile
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any


class OutputFormat(Enum):
    """Supported output formats for password managers."""
    ICLOUD_PASSWORDS = "icloud"


class BasePasswordExporter(ABC):
    """Base class for password manager exporters."""
    
    def __init__(self, output_dir: Path, filename_stem: str):
        self.output_dir = output_dir
        self.filename_stem = filename_stem
    
    @abstractmethod
    def get_fieldnames(self) -> List[str]:
        """Get the CSV fieldnames for this format."""
        pass
    
    @abstractmethod
    def transform_item(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Transform a password item to the format-specific structure."""
        pass
    
    @abstractmethod
    def get_output_filename(self) -> str:
        """Get the output filename for this format."""
        pass
    
    def export(self, password_items: List[Dict[str, Any]]) -> Path:
        """Export password items to CSV file."""
        output_file = self.output_dir / self.get_output_filename()
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.get_fieldnames())
                writer.writeheader()
                
                for item in password_items:
                    transformed_item = self.transform_item(item)
                    writer.writerow(transformed_item)
            
            return output_file
            
        except IOError as e:
            raise IOError(f"Failed to write CSV file: {e}")


class iCloudPasswordsExporter(BasePasswordExporter):
    """Exporter for iCloud Passwords format."""
    
    def get_fieldnames(self) -> List[str]:
        return ['Title', 'URL', 'Username', 'Password', 'Notes', 'OTPAuth']
    
    def transform_item(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Transform item to iCloud Passwords format."""
        return {
            'Title': item.get('title', ''),
            'URL': item.get('url', ''),
            'Username': item.get('username', ''),
            'Password': item.get('password', ''),
            'Notes': item.get('notes', ''),
            'OTPAuth': item.get('otp_auth', '')
        }
    
    def get_output_filename(self) -> str:
        return f"{self.filename_stem}_icloud.csv"


class PasswordExporterFactory:
    """Factory for creating password exporters."""
    
    @staticmethod
    def create_exporter(format_type: OutputFormat, output_dir: Path, filename_stem: str) -> BasePasswordExporter:
        """Create an exporter instance based on the format type."""
        if format_type == OutputFormat.ICLOUD_PASSWORDS:
            return iCloudPasswordsExporter(output_dir, filename_stem)
        else:
            raise ValueError(f"Unsupported format: {format_type}")


class OnePasswordConverter:
    """Converts 1Password .1pux files to various password manager formats."""
    
    def __init__(self, input_file: Path, output_dir: Optional[Path] = None, output_format: OutputFormat = OutputFormat.ICLOUD_PASSWORDS):
        self.input_file = input_file
        self.output_dir = output_dir or input_file.parent
        self.output_format = output_format
        self.password_items: List[Dict[str, Any]] = []
        self.logger = self._setup_logging()
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def _validate_input_file(self) -> None:
        """Validate the input file exists and has correct extension."""
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
        
        if not self.input_file.is_file():
            raise ValueError(f"Path is not a file: {self.input_file}")
        
        if self.input_file.suffix.lower() != '.1pux':
            raise ValueError(f"Invalid file extension. Expected .1pux, got {self.input_file.suffix}")
    
    def _extract_1password_file(self, temp_dir: Path) -> Path:
        """Extract the 1Password file to a temporary directory."""
        try:
            with zipfile.ZipFile(self.input_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            export_data_file = temp_dir / 'export.data'
            if not export_data_file.exists():
                raise FileNotFoundError("export.data not found in the archive")
            
            return export_data_file
        except zipfile.BadZipFile:
            raise ValueError(f"Invalid or corrupted 1Password file: {self.input_file}")
    
    def _parse_login_fields(self, login_fields: List[Dict]) -> tuple[Optional[str], Optional[str]]:
        """Parse login fields to extract username and password."""
        username = None
        password = None
        
        for field in login_fields:
            if not isinstance(field, dict) or 'name' not in field or 'value' not in field:
                continue
            
            field_name = field['name'].lower()
            if field_name == 'username':
                username = field['value']
            elif field_name == 'password':
                password = field['value']
        
        return username, password
    
    def _convert_to_keychain(self, export_data_file: Path) -> None:
        """Convert 1Password data to internal format."""
        try:
            with open(export_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in export.data: {e}")
        
        # Navigate the JSON structure safely
        accounts = data.get('accounts', [])
        if not accounts:
            raise ValueError("No accounts found in the export data")
        
        vaults = accounts[0].get('vaults', [])
        if not vaults:
            raise ValueError("No vaults found in the first account")
        
        items = vaults[0].get('items', [])
        self.logger.info(f"Processing {len(items)} items from 1Password export")
        
        for item in items:
            try:
                overview = item.get('overview', {})
                details = item.get('details', {})
                
                title = overview.get('title', 'Untitled')
                url = overview.get('url', '')
                
                username, password = None, None
                login_fields = details.get('loginFields', [])
                if login_fields:
                    username, password = self._parse_login_fields(login_fields)
                
                # Store in generic format
                password_item = {
                    'title': title,
                    'url': url,
                    'username': username or '',
                    'password': password or '',
                    'notes': '',
                    'otp_auth': ''
                }
                
                self.password_items.append(password_item)
                
            except Exception as e:
                self.logger.warning(f"Skipping item due to error: {e}")
                continue
    
    def _export_passwords(self) -> Path:
        """Export password items using the specified format."""
        exporter = PasswordExporterFactory.create_exporter(
            self.output_format, 
            self.output_dir, 
            self.input_file.stem
        )
        
        output_file = exporter.export(self.password_items)
        self.logger.info(f"Successfully exported {len(self.password_items)} items to {output_file}")
        return output_file
    
    def convert(self) -> Path:
        """Main conversion method."""
        self._validate_input_file()
        self.logger.info(f"Starting conversion of {self.input_file} to {self.output_format.value} format")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract and convert
            export_data_file = self._extract_1password_file(temp_path)
            self._convert_to_keychain(export_data_file)
            output_file = self._export_passwords()
            
            return output_file


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Convert 1Password .1pux files to various password manager formats",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'input_file',
        type=Path,
        help='Path to the 1Password .1pux file'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        type=Path,
        help='Output directory for the CSV file (default: same as input file)'
    )
    
    parser.add_argument(
        '-f', '--format',
        type=str,
        choices=[f.value for f in OutputFormat],
        default=OutputFormat.ICLOUD_PASSWORDS.value,
        help='Output format for password manager (default: icloud)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Convert format string to enum
        output_format = OutputFormat(args.format)
        
        converter = OnePasswordConverter(args.input_file, args.output_dir, output_format)
        output_file = converter.convert()
        print(f"Conversion successful! Output saved to: {output_file}")
        
    except (FileNotFoundError, ValueError, IOError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
