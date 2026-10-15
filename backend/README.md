# Backend API

FastAPI backend for the Multi-Agent Data Analyst system.

## Purpose

This API provides endpoints for:
- Excel Add-in integration
- File upload and data profiling
- Chat-based data analysis
- Persistent data storage

## Running the Backend

```bash
cd backend
python api.py
```

The server will run on http://localhost:8000

## API Endpoints

### GET /
**Status check**
```json
{
  "message": "Multi-Agent Data Analyst API",
  "status": "running",
  "version": "1.0.0"
}
```

### POST /api/upload
**Upload a data file**

**Request:** multipart/form-data with file field

**Response:**
```json
{
  "success": true,
  "filename": "data.csv",
  "profile": {
    "rows": 1000,
    "columns": 5,
    "column_names": ["col1", "col2", ...],
    "dtypes": {...},
    "missing_values": {...}
  }
}
```

### POST /api/chat
**Ask questions about uploaded data**

**Request:**
```json
{
  "question": "How many rows?",
  "context": {}
}
```

**Response:**
```json
{
  "success": true,
  "question": "How many rows?",
  "response": "Your dataset has 1000 rows..."
}
```

### GET /api/status
**Check if data is uploaded**

**Response:**
```json
{
  "has_data": true,
  "profile": {...}
}
```

## Supported Questions

- Row/column counts
- Column names
- Data types
- Missing values
- Summary statistics
- First few rows
- Average/mean values
- Maximum/minimum values

## Data Storage

Uploaded data is stored in:
- File: `temp/{filename}`
- Metadata: `temp/uploaded_data.json`

Data persists across server restarts.

## CORS

CORS is enabled for all origins to support:
- Excel Add-in (Office.js)
- Local development
- Future frontend integrations

## Excel Add-in Integration

The Excel Add-in can call:
- `POST /api/upload` - Upload data from Excel
- `POST /api/chat` - Ask questions about the data
- `GET /api/status` - Check if data is available

## Example Usage

```python
import requests

# Upload file
with open('data.csv', 'rb') as f:
    response = requests.post('http://localhost:8000/api/upload', files={'file': f})

# Ask question
response = requests.post('http://localhost:8000/api/chat', json={
    'question': 'How many rows?'
})
print(response.json()['response'])
```
