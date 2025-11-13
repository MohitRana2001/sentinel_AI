import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from redis_pubsub import redis_pubsub
from storage_config import storage_manager
from config import settings
from database import SessionLocal
import models
from cdr_processor import CDRProcessor
import traceback
from datetime import datetime, timezone
import re


class CDRProcessorService:
    
    def __init__(self):
        print(f"CDR Processor Service initialized")
    
    def process_job(self, message: dict):
        print(f"\n{'='*60}")
        print(f"Received message from CDR queue")
        print(f"Message: {message}")
        print(f"{'='*60}\n")

        action = message.get("action", "process")
        job_id = message.get("job_id")
        
        print(f"Action: {action}, Job ID: {job_id}")
        
        if action == "process_file":
            self._process_single_file(message)
        else:
            print(f"Unknown action: {action}")
    
    def _process_single_file(self, message: dict):
        job_id = message.get("job_id")
        gcs_path = message.get("gcs_path")
        filename = message.get("filename")
        
        print(f"\nCDR Processor received file: {filename} (job: {job_id})")
        print(f"GCS Path: {gcs_path}")
        
        db = SessionLocal()
        artifact_start_time = datetime.now(timezone.utc)
        
        try:
            # Get job from database
            job = db.query(models.ProcessingJob).filter(
                models.ProcessingJob.id == job_id
            ).first()
            
            if not job:
                print(f"Job {job_id} not found")
                return
            
            if job.status == models.JobStatus.QUEUED:
                job.status = models.JobStatus.PROCESSING
                job.started_at = datetime.now(timezone.utc)
                db.commit()
                print(f"Job status updated to PROCESSING")
            
            # Check if this file has already been processed (distributed lock)
            existing_cdr = db.query(models.CDRRecord).filter(
                models.CDRRecord.job_id == job.id,
                models.CDRRecord.original_filename == filename
            ).first()
            
            if existing_cdr and existing_cdr.data:
                print(f"File {filename} already processed by another worker, skipping")
                return
            
            # Create or update CDR record with PROCESSING status
            if not existing_cdr:
                existing_cdr = models.CDRRecord(
                    job_id=job.id,
                    original_filename=filename,
                    file_path=gcs_path,
                    data=[],
                    record_count=0,
                    status=models.JobStatus.PROCESSING,
                    started_at=artifact_start_time,
                    processing_stages={}
                )
                db.add(existing_cdr)
            else:
                existing_cdr.status = models.JobStatus.PROCESSING
                existing_cdr.started_at = artifact_start_time
                existing_cdr.processing_stages = {}
            
            db.commit()
            
            # Publish artifact status: PROCESSING
            redis_pubsub.publish_artifact_status(
                job_id=job_id,
                filename=filename,
                status="processing",
                current_stage="parsing",
                file_type="cdr"
            )
            
            # Process the CDR file
            self.process_cdr(db, job, gcs_path, existing_cdr, artifact_start_time)
            
            self._check_job_completion(db, job)
            
            print(f"Completed processing: {filename}\n")
            
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            traceback.print_exc()
            
            # Update CDR record status to FAILED
            try:
                cdr = db.query(models.CDRRecord).filter(
                    models.CDRRecord.job_id == job_id,
                    models.CDRRecord.original_filename == filename
                ).first()
                
                if cdr:
                    cdr.status = models.JobStatus.FAILED
                    cdr.error_message = str(e)
                    cdr.completed_at = datetime.now(timezone.utc)
                    db.commit()
                    
                    # Publish artifact status: FAILED
                    redis_pubsub.publish_artifact_status(
                        job_id=job_id,
                        filename=filename,
                        status="failed",
                        error_message=str(e)
                    )
            except Exception as update_error:
                print(f"Failed to update CDR record status: {update_error}")
        finally:
            db.close()
    
    def _check_job_completion(self, db, job):
        # Count total files expected
        total_files = job.total_files
        
        # Count documents processed
        documents_count = db.query(models.Document).filter(
            models.Document.job_id == job.id,
            models.Document.status == models.JobStatus.COMPLETED
        ).count()
        
        # Count CDR files processed
        cdr_count = db.query(models.CDRRecord).filter(
            models.CDRRecord.job_id == job.id,
            models.CDRRecord.status == models.JobStatus.COMPLETED
        ).count()
        
        total_processed = documents_count + cdr_count
        
        print(f"Job {job.id}: {total_processed}/{total_files} files processed")
        
        if total_processed >= total_files:
            if job.status != models.JobStatus.COMPLETED:
                job.status = models.JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                print(f"Job {job.id}: all files processed - COMPLETED")
        elif total_processed > 0:
            if job.status == models.JobStatus.QUEUED:
                job.status = models.JobStatus.PROCESSING
                job.started_at = job.started_at or datetime.now(timezone.utc)
                db.commit()
    
    def process_cdr(self, db, job, gcs_path: str, cdr_record, artifact_start_time):
        print(f"\n🔄 Processing CDR: {gcs_path}")
        
        stage_times = {}
        
        try:
            filename = os.path.basename(gcs_path)
            
            # Stage 1: Parsing CDR file
            cdr_record.current_stage = "parsing"
            db.commit()
            redis_pubsub.publish_artifact_status(
                job_id=job.id,
                filename=filename,
                status="processing",
                current_stage="parsing",
                file_type="cdr"
            )
            
            parsing_start = datetime.now(timezone.utc)
            
            # Download and parse CDR file
            cdr_data = CDRProcessor.process_cdr_file(gcs_path)
            CDRProcessor.validate_cdr_data(cdr_data)
            
            parsing_time = (datetime.now(timezone.utc) - parsing_start).total_seconds()
            stage_times["parsing"] = parsing_time
            
            print(f"✅ Parsed {len(cdr_data)} CDR records in {parsing_time:.2f}s")
            
            # Stage 2: Phone number matching with POI
            cdr_record.current_stage = "phone_matching"
            cdr_record.processing_stages = stage_times
            db.commit()
            redis_pubsub.publish_artifact_status(
                job_id=job.id,
                filename=filename,
                status="processing",
                current_stage="phone_matching",
                processing_stages=stage_times,
                file_type="cdr"
            )
            
            matching_start = datetime.now(timezone.utc)
            
            # Match phone numbers with Person of Interest
            matches = self._match_phone_numbers(db, job.id, cdr_data)
            
            matching_time = (datetime.now(timezone.utc) - matching_start).total_seconds()
            stage_times["phone_matching"] = matching_time
            
            print(f"✅ Found {len(matches)} phone number matches in {matching_time:.2f}s")
            
            # Save CDR data
            cdr_record.data = cdr_data
            cdr_record.record_count = len(cdr_data)
            cdr_record.status = models.JobStatus.COMPLETED
            cdr_record.completed_at = datetime.now(timezone.utc)
            cdr_record.processing_stages = stage_times
            cdr_record.current_stage = "completed"
            db.commit()
            
            # Update job progress
            job.processed_files += 1
            db.commit()
            
            # Publish completion
            redis_pubsub.publish_artifact_status(
                job_id=job.id,
                filename=filename,
                status="completed",
                current_stage="completed",
                processing_stages=stage_times,
                file_type="cdr"
            )
            
            print(f"✅ CDR processing completed: {filename}")
            
        except Exception as e:
            print(f"❌ Error processing CDR: {e}")
            traceback.print_exc()
            
            cdr_record.status = models.JobStatus.FAILED
            cdr_record.error_message = str(e)
            cdr_record.completed_at = datetime.now(timezone.utc)
            db.commit()
            
            redis_pubsub.publish_artifact_status(
                job_id=job.id,
                filename=os.path.basename(gcs_path),
                status="failed",
                error_message=str(e)
            )
            raise
    
    def _match_phone_numbers(self, db, job_id, cdr_data):
        """
        Match phone numbers in CDR data with Person of Interest records
        Returns list of matches and creates CDR_POI_Match records
        """
        # Get all POI records with phone numbers
        pois = db.query(models.PersonOfInterest).all()
        
        matches = []
        
        # Extract phone numbers from POI details
        poi_phones = {}
        for poi in pois:
            details = poi.details or {}
            
            # Look for phone number in various possible keys
            phone_keys = ['phone', 'phone_number', 'mobile', 'mobile_number', 'contact', 'telephone']
            
            for key in phone_keys:
                if key in details:
                    phone_value = details[key]
                    # Handle if phone_value is a list or single value
                    if isinstance(phone_value, list):
                        for phone in phone_value:
                            normalized = self._normalize_phone(str(phone))
                            if normalized:
                                poi_phones[normalized] = poi.id
                    else:
                        normalized = self._normalize_phone(str(phone_value))
                        if normalized:
                            poi_phones[normalized] = poi.id
        
        print(f"Found {len(poi_phones)} unique phone numbers across {len(pois)} POIs")
        
        # Match CDR records with POI phone numbers
        for cdr_record in cdr_data:
            # Extract phone numbers from CDR record
            # Common CDR fields: caller, called, calling_number, called_number, a_number, b_number
            phone_fields = ['caller', 'called', 'calling_number', 'called_number', 
                          'a_number', 'b_number', 'source', 'destination']
            
            for field in phone_fields:
                if field in cdr_record and cdr_record[field]:
                    phone = self._normalize_phone(str(cdr_record[field]))
                    
                    if phone and phone in poi_phones:
                        poi_id = poi_phones[phone]
                        
                        # Create CDR-POI match record
                        match = models.CDRPOIMatch(
                            job_id=job_id,
                            poi_id=poi_id,
                            phone_number=phone,
                            cdr_record_data=cdr_record,
                            matched_field=field
                        )
                        db.add(match)
                        matches.append({
                            'poi_id': poi_id,
                            'phone': phone,
                            'field': field
                        })
        
        if matches:
            db.commit()
            print(f"Created {len(matches)} CDR-POI match records")
        
        return matches
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number by removing spaces, dashes, parentheses
        Returns only digits
        """
        if not phone:
            return ""
        
        # Remove all non-digit characters
        normalized = re.sub(r'\D', '', phone)
        
        # Return only if we have a reasonable phone number length
        if len(normalized) >= 10:
            return normalized
        
        return ""


def main():
    """Main function to run CDR processor service"""
    service = CDRProcessorService()
    
    print("Starting CDR Processor Service...")
    print(f"Listening on Redis queue: {settings.REDIS_QUEUE_CDR}")
    
    def process_message(message_data):
        try:
            service.process_job(message_data)
        except Exception as e:
            print(f"Error in CDR processor: {e}")
            traceback.print_exc()
    
    # Subscribe to CDR queue
    redis_pubsub.subscribe_to_queue(
        settings.REDIS_QUEUE_CDR,
        process_message
    )


if __name__ == "__main__":
    main()
