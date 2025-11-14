"""
CDR (Call Data Records) Processor
Converts CSV/XLSX CDR files to JSONB format
"""
import pandas as pd
import io
from typing import List, Dict, Any
from storage_config import storage_manager


class CDRProcessor:
    """Process CDR files (CSV/XLSX) and convert to JSONB format"""
    
    @staticmethod
    def detect_header_row(file_content: bytes) -> int:
        """
        Detect the actual header row in a CSV file that may have metadata at the top.
        
        Args:
            file_content: Bytes content of CSV file
            
        Returns:
            Row index where the actual data header is located (0-indexed)
        """
        lines = file_content.decode('utf-8', errors='ignore').split('\n')
        
        # Look for the first row that has multiple comma-separated values
        # and appears to be a consistent header
        max_columns = 0
        header_row = 0
        
        for idx, line in enumerate(lines[:20]):  # Check first 20 lines
            if not line.strip():
                continue
            
            # Count commas (potential columns)
            column_count = line.count(',')
            
            # If this row has more columns than previous, it might be the header
            if column_count > max_columns and column_count > 3:  # Assume CDR has at least 4 columns
                max_columns = column_count
                header_row = idx
        
        return header_row
    
    @staticmethod
    def process_csv(file_content: bytes) -> List[Dict[str, Any]]:
        """
        Process CSV file and convert to list of dictionaries.
        Handles various CSV formats including those with metadata headers.
        
        Args:
            file_content: Bytes content of CSV file
            
        Returns:
            List of dictionaries representing call records
        """
        try:
            # Try standard CSV parsing first
            try:
                df = pd.read_csv(io.BytesIO(file_content))
                
                # Check if we got valid data
                if df.empty or df.shape[1] <= 1:
                    raise pd.errors.ParserError("Insufficient columns detected")
                    
            except (pd.errors.ParserError, pd.errors.EmptyDataError):
                # If standard parsing fails, detect the actual header row
                header_row = CDRProcessor.detect_header_row(file_content)
                df = pd.read_csv(
                    io.BytesIO(file_content),
                    skiprows=header_row,
                    on_bad_lines='skip',  # Skip malformed lines
                    encoding='utf-8',
                    encoding_errors='ignore'
                )
            
            # If DataFrame is empty or has no valid data, try alternative approaches
            if df.empty or df.shape[1] <= 1:
                # Try comma-separated with explicit delimiter
                try:
                    df = pd.read_csv(
                        io.BytesIO(file_content),
                        sep=',',
                        skipinitialspace=True,
                        on_bad_lines='skip'
                    )
                except:
                    # Try tab-separated
                    df = pd.read_csv(
                        io.BytesIO(file_content),
                        sep='\t',
                        on_bad_lines='skip'
                    )
            
            # Remove completely empty rows
            df = df.dropna(how='all')
            
            # If still empty, raise error
            if df.empty:
                raise ValueError("CSV file contains no valid data rows")
            
            # Convert DataFrame to list of dictionaries
            records = df.to_dict(orient='records')
            
            # Clean up NaN values (convert to None for JSON)
            cleaned_records = []
            for record in records:
                cleaned_record = {
                    k: (None if pd.isna(v) else v)
                    for k, v in record.items()
                }
                cleaned_records.append(cleaned_record)
            
            return cleaned_records
        except Exception as e:
            raise ValueError(f"Error processing CSV: {str(e)}")
    
    @staticmethod
    def process_xlsx(file_content: bytes) -> List[Dict[str, Any]]:
        """
        Process XLSX file and convert to list of dictionaries
        
        Args:
            file_content: Bytes content of XLSX file
            
        Returns:
            List of dictionaries representing call records
        """
        try:
            # Read XLSX into pandas DataFrame
            df = pd.read_excel(io.BytesIO(file_content))
            
            # Convert DataFrame to list of dictionaries
            records = df.to_dict(orient='records')
            
            # Clean up NaN values (convert to None for JSON)
            cleaned_records = []
            for record in records:
                cleaned_record = {
                    k: (None if pd.isna(v) else str(v) if not pd.isna(v) else None)
                    for k, v in record.items()
                }
                cleaned_records.append(cleaned_record)
            
            return cleaned_records
        except Exception as e:
            raise ValueError(f"Error processing XLSX: {str(e)}")
    
    @staticmethod
    def process_cdr_file(gcs_path: str) -> List[Dict[str, Any]]:
        """
        Download and process CDR file from GCS/local storage
        
        Args:
            gcs_path: Path to CDR file in storage
            
        Returns:
            List of dictionaries representing call records
        """
        # Determine file type and download to temp
        suffix = '.csv' if gcs_path.lower().endswith('.csv') else '.xlsx'
        temp_file_path = storage_manager.download_to_temp(gcs_path, suffix=suffix)
        
        try:
            # Read file content as bytes
            with open(temp_file_path, 'rb') as f:
                file_content = f.read()
            
            # Process based on file type
            if gcs_path.lower().endswith('.csv'):
                return CDRProcessor.process_csv(file_content)
            elif gcs_path.lower().endswith(('.xlsx', '.xls')):
                return CDRProcessor.process_xlsx(file_content)
            else:
                raise ValueError(f"Unsupported CDR file format: {gcs_path}")
        finally:
            # Clean up temp file
            import os
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    @staticmethod
    def validate_cdr_data(records: List[Dict[str, Any]]) -> bool:
        """
        Validate CDR data structure
        
        Args:
            records: List of call records
            
        Returns:
            True if valid, raises ValueError if invalid
        """
        if not records:
            raise ValueError("CDR file is empty")
        
        if not isinstance(records, list):
            raise ValueError("CDR data must be a list of records")
        
        # Check if all records are dictionaries
        for i, record in enumerate(records):
            if not isinstance(record, dict):
                raise ValueError(f"Record {i} is not a dictionary")
        
        return True


# Singleton instance
cdr_processor = CDRProcessor()
