# Configurable Storage System

A production-ready, extensible storage abstraction layer for Sentinel AI that supports multiple cloud providers and local storage.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# For Google Cloud Storage
pip install google-cloud-storage

# For Amazon S3
pip install boto3

# For local storage (no additional dependencies needed)
```

### 2. Configure Storage Backend

Set environment variables in `.env`:

```bash
# Choose backend: 'gcs', 's3', 'local', 'azure'
STORAGE_BACKEND=gcs

# Configure your chosen backend (see .env.example for all options)
GCS_BUCKET_NAME=my-bucket
```

### 3. Use in Your Code

```python
from storage_config import storage_manager

# Upload
storage_manager.upload_text("Hello World", "greeting.txt")

# Download
content = storage_manager.download_text("greeting.txt")

# List files
files = storage_manager.list_files("documents/")
```

## 📚 Documentation

See [STORAGE_CONFIGURATION_GUIDE.md](../STORAGE_CONFIGURATION_GUIDE.md) for complete documentation including:

- Detailed architecture overview
- All supported backends
- Configuration examples
- Migration guide from legacy code
- Adding custom backends
- Troubleshooting
- Best practices

## 🎯 Features

✅ **Multiple Backends**: GCS, S3, Local, Azure (coming soon)  
✅ **Simple Configuration**: Environment variables  
✅ **Auto-Fallback**: Automatically uses local storage if cloud fails  
✅ **Backward Compatible**: Works with existing code  
✅ **Production Ready**: Error handling, retries, health checks  
✅ **Extensible**: Easy to add new backends  
✅ **Type Safe**: Full type hints throughout  

## 🏗️ Architecture

```
Application Code
      ↓
storage_manager (Singleton)
      ↓
StorageBackend (Interface)
      ↓
┌─────────┬─────────┬─────────┬─────────┐
│   GCS   │   S3    │  Local  │  Azure  │
└─────────┴─────────┴─────────┴─────────┘
```

## 🔧 Supported Backends

| Backend | Status | Use Case |
|---------|--------|----------|
| **Google Cloud Storage** | ✅ Ready | GCP production deployments |
| **Amazon S3** | ✅ Ready | AWS production deployments |
| **Local Filesystem** | ✅ Ready | Development, testing, edge |
| **Azure Blob Storage** | 🚧 Coming Soon | Azure production deployments |

## 💡 Examples

### Switch to S3

```bash
# .env
STORAGE_BACKEND=s3
S3_BUCKET_NAME=my-bucket
S3_REGION_NAME=us-east-1
```

### Use Local Storage

```bash
# .env
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./storage
```

### Use MinIO (S3-compatible)

```bash
# .env
STORAGE_BACKEND=s3
S3_BUCKET_NAME=sentinel
S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
```

## 🛠️ Module Structure

```
storage/
├── __init__.py           # Package exports
├── base.py              # Abstract interface & exceptions
├── gcs_backend.py       # Google Cloud Storage
├── s3_backend.py        # Amazon S3
├── local_backend.py     # Local filesystem
├── factory.py           # Factory for creating backends
├── manager.py           # Singleton manager
├── .env.example         # Configuration examples
└── README.md           # This file
```

## 🔄 Migration from Legacy Code

Old code:
```python
from gcs_storage import gcs_storage
gcs_storage.upload_text("content", "file.txt")
```

New code:
```python
from storage_config import storage_manager
storage_manager.upload_text("content", "file.txt")
```

That's it! The storage backend is now configurable.

## 🧪 Testing

```bash
# Test with local storage
export STORAGE_BACKEND=local
python -m pytest tests/

# Test with GCS
export STORAGE_BACKEND=gcs
export GCS_BUCKET_NAME=test-bucket
python -m pytest tests/
```

## 📝 API Reference

### Core Methods

```python
# Upload operations
storage_manager.upload_file(file_obj, remote_path) -> str
storage_manager.upload_from_filename(local_path, remote_path) -> str
storage_manager.upload_text(text, remote_path) -> str

# Download operations
storage_manager.download_file(remote_path, local_path) -> str
storage_manager.download_to_temp(remote_path, suffix=None) -> str
storage_manager.download_text(remote_path) -> str

# File operations
storage_manager.list_files(prefix) -> List[str]
storage_manager.delete_file(remote_path) -> None
storage_manager.file_exists(remote_path) -> bool

# Utility methods
storage_manager.get_backend_type() -> str
storage_manager.health_check() -> bool
storage_manager.get_info() -> dict
```

## 🎓 Advanced Usage

### Custom Backend Configuration

```python
from storage import StorageFactory, storage_manager

# Create custom backend
config = {'bucket_name': 'custom-bucket'}
backend = StorageFactory.create_backend('gcs', config)

# Initialize manager
storage_manager.initialize(backend)
```

### Health Monitoring

```python
if not storage_manager.health_check():
    # Alert or fallback
    print("Storage is unavailable!")
```

### Batch Operations

```python
files_to_upload = ["file1.txt", "file2.txt", "file3.txt"]
for file in files_to_upload:
    storage_manager.upload_from_filename(file, f"uploads/{file}")
```

## 🤝 Contributing

Want to add a new storage backend? See the "Adding New Storage Backends" section in [STORAGE_CONFIGURATION_GUIDE.md](../STORAGE_CONFIGURATION_GUIDE.md).

## 📄 License

Part of Sentinel AI project. All rights reserved.

## 🆘 Support

- Full documentation: [STORAGE_CONFIGURATION_GUIDE.md](../STORAGE_CONFIGURATION_GUIDE.md)
- Example configuration: `.env.example`
- Issues: Check project repository

---

**Made with ❤️ for flexible, production-ready storage**

