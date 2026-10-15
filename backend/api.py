from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sys
import os
import pandas as pd
import json

# Add parent directory to path to import from main project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(title="Multi-Agent Data Analyst API")

# CORS middleware - allow Excel Add-in and any frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Excel Add-in
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent storage file
STORAGE_FILE = "temp/uploaded_data.json"

def load_data():
    """Load uploaded data from storage"""
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, 'r') as f:
            data = json.load(f)
            # Convert stored DataFrame back
            if data.get("file_path") and os.path.exists(data["file_path"]):
                try:
                    df = pd.read_csv(data["file_path"]) if data["file_path"].endswith('.csv') else pd.read_excel(data["file_path"])
                    data["df"] = df
                except:
                    data["df"] = None
            return data
    return {"file_path": None, "df": None, "profile": None}

def save_data(data):
    """Save uploaded data to storage"""
    # Don't save the actual DataFrame, just the file path and profile
    save_data = {
        "file_path": data.get("file_path"),
        "profile": data.get("profile")
    }
    with open(STORAGE_FILE, 'w') as f:
        json.dump(save_data, f)

class ChatRequest(BaseModel):
    question: str
    context: dict = None

@app.get("/")
async def root():
    return {"message": "Multi-Agent Data Analyst API", "status": "running", "version": "1.0.0"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and profile a data file - for Excel Add-in and other clients"""
    try:
        # Create temp directory if it doesn't exist
        os.makedirs("temp", exist_ok=True)
        
        # Save uploaded file
        file_path = f"temp/{file.filename}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Read and profile the data
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            profile = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "dtypes": df.dtypes.astype(str).to_dict(),
                "missing_values": df.isnull().sum().to_dict()
            }
            
            # Save to persistent storage
            save_data({
                "file_path": file_path,
                "df": df,
                "profile": profile
            })
            
            return {
                "success": True,
                "filename": file.filename,
                "profile": profile
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to read file: {str(e)}"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat interface for data analysis - for Excel Add-in and other clients"""
    try:
        # Load data from persistent storage
        data = load_data()
        
        # Check if data is uploaded
        if data["df"] is None:
            return {
                "success": True,
                "question": request.question,
                "response": "Please upload a CSV or Excel file first using the upload section. Once uploaded, you can ask questions about your data!"
            }
        
        # Get data info
        profile = data["profile"]
        columns = profile["column_names"]
        df = data["df"]
        
        # Simple analysis based on question
        question_lower = request.question.lower()
        
        # Check for common queries
        if 'row' in question_lower and 'column' in question_lower:
            response = f"Your dataset has {profile['rows']} rows and {profile['columns']} columns.\n\nColumns: {', '.join(columns)}"
        elif 'column' in question_lower and 'name' in question_lower:
            response = f"The columns in your dataset are: {', '.join(columns)}"
        elif 'type' in question_lower or 'dtype' in question_lower:
            dtype_info = "\n".join([f"{col}: {dtype}" for col, dtype in profile["dtypes"].items()])
            response = f"Column data types:\n{dtype_info}"
        elif 'missing' in question_lower or 'null' in question_lower:
            missing_info = "\n".join([f"{col}: {count}" for col, count in profile["missing_values"].items() if count > 0])
            if missing_info:
                response = f"Missing values:\n{missing_info}"
            else:
                response = "There are no missing values in your dataset."
        elif 'describe' in question_lower or 'summary' in question_lower:
            summary = df.describe().to_string()
            response = f"Dataset summary:\n{summary}"
        elif 'head' in question_lower or 'first' in question_lower:
            head = df.head().to_string()
            response = f"First 5 rows:\n{head}"
        elif 'average' in question_lower or 'mean' in question_lower:
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                means = df[numeric_cols].mean().to_string()
                response = f"Average values:\n{means}"
            else:
                response = "No numeric columns found in the dataset."
        elif 'max' in question_lower or 'maximum' in question_lower:
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                maxs = df[numeric_cols].max().to_string()
                response = f"Maximum values:\n{maxs}"
            else:
                response = "No numeric columns found in the dataset."
        elif 'min' in question_lower or 'minimum' in question_lower:
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                mins = df[numeric_cols].min().to_string()
                response = f"Minimum values:\n{mins}"
            else:
                response = "No numeric columns found in the dataset."
        else:
            response = f"I understand you want to: {request.question}\n\nYour dataset has {profile['rows']} rows and {profile['columns']} columns: {', '.join(columns)}.\n\nYou can ask me about:\n- Row/column counts\n- Column names\n- Data types\n- Missing values\n- Summary statistics\n- First few rows\n- Average/mean values\n- Maximum/minimum values"
        
        return {
            "success": True,
            "question": request.question,
            "response": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def status():
    """Check if data is uploaded"""
    data = load_data()
    return {
        "has_data": data["df"] is not None,
        "profile": data["profile"] if data["df"] is not None else None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
