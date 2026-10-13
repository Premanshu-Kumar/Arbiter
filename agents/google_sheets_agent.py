"""
Google Sheets Integration - Phase 8

Handles Google Sheets operations including:
- OAuth authentication
- Spreadsheet selection
- Sheet data retrieval
- Result write-back
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import os
import json


class GoogleSheetsIntegrator:
    """
    Google Sheets integration for data analysis.
    
    Supports:
    - OAuth authentication
    - Spreadsheet selection
    - Sheet data retrieval
    - Result write-back
    - Sheet management
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Sheets integrator.
        
        Args:
            credentials_path: Path to Google OAuth credentials JSON file
        """
        self.credentials_path = credentials_path
        self.client = None
        self.service = None
        self.spreadsheet_id: Optional[str] = None
        self.is_authenticated = False
    
    def authenticate(self, credentials_json: Optional[str] = None) -> Dict[str, Any]:
        """
        Authenticate with Google Sheets API using OAuth.
        
        Args:
            credentials_json: Google credentials as JSON string
        
        Returns:
            Authentication status
        """
        try:
            if credentials_json:
                # Parse credentials from JSON string
                credentials_dict = json.loads(credentials_json)
                # Save temporarily
                temp_path = "temp_credentials.json"
                with open(temp_path, 'w') as f:
                    json.dump(credentials_dict, f)
                self.credentials_path = temp_path
            
            # Try to import and authenticate
            try:
                from google.oauth2.service_account import Credentials
                from googleapiclient.discovery import build
                
                if self.credentials_path and os.path.exists(self.credentials_path):
                    credentials = Credentials.from_service_account_file(
                        self.credentials_path,
                        scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
                    
                    self.service = build('sheets', 'v4', credentials=credentials)
                    self.is_authenticated = True
                    
                    return {
                        "success": True,
                        "message": "Successfully authenticated with Google Sheets API"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Credentials file not found",
                        "message": "Please provide valid Google credentials JSON"
                    }
                    
            except ImportError:
                return {
                    "success": False,
                    "error": "Google libraries not installed",
                    "message": "Install required packages: pip install google-api-python-client google-auth"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Authentication failed: {str(e)}"
            }
    
    def list_spreadsheets(self) -> Dict[str, Any]:
        """
        List available spreadsheets.
        
        Returns:
            List of spreadsheets
        """
        if not self.is_authenticated:
            return {
                "success": False,
                "error": "Not authenticated",
                "message": "Please authenticate first"
            }
        
        try:
            # Use Drive API to list spreadsheets
            # For now, return a mock implementation
            return {
                "success": True,
                "spreadsheets": [],
                "message": "Drive API integration required for listing"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to list spreadsheets: {str(e)}"
            }
    
    def load_spreadsheet(self, spreadsheet_id: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load data from a Google Spreadsheet.
        
        Args:
            spreadsheet_id: Google Spreadsheet ID
            sheet_name: Specific sheet name (optional)
        
        Returns:
            Loaded data as DataFrame
        """
        if not self.is_authenticated:
            return {
                "success": False,
                "error": "Not authenticated",
                "message": "Please authenticate first"
            }
        
        self.spreadsheet_id = spreadsheet_id
        
        try:
            # Get spreadsheet metadata
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheet_names = [sheet['properties']['title'] 
                          for sheet in spreadsheet['sheets']]
            
            # Load data from specified sheet or first sheet
            target_sheet = sheet_name if sheet_name else sheet_names[0]
            
            # Get sheet data
            range_name = f"{target_sheet}!A1:Z1000"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                return {
                    "success": False,
                    "error": "No data found",
                    "message": f"Sheet '{target_sheet}' is empty"
                }
            
            # Convert to DataFrame
            df = pd.DataFrame(values[1:], columns=values[0])
            
            return {
                "success": True,
                "data": df,
                "sheet_name": target_sheet,
                "sheet_names": sheet_names,
                "rows": len(df),
                "columns": len(df.columns),
                "message": f"Loaded {len(df)} rows from '{target_sheet}'"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to load spreadsheet: {str(e)}"
            }
    
    def write_results(
        self,
        results: Dict[str, Any],
        sheet_name: str = "Analysis Results"
    ) -> Dict[str, Any]:
        """
        Write analysis results back to Google Sheets.
        
        Args:
            results: Analysis results dictionary
            sheet_name: Target sheet name
        
        Returns:
            Write status
        """
        if not self.is_authenticated or not self.spreadsheet_id:
            return {
                "success": False,
                "error": "Not authenticated or no spreadsheet selected",
                "message": "Please authenticate and select a spreadsheet first"
            }
        
        try:
            # Prepare data to write
            data_to_write = []
            
            # Add headers
            if results.get('result') is not None:
                if isinstance(results['result'], pd.DataFrame):
                    data_to_write.append(results['result'].columns.tolist())
                    data_to_write.extend(results['result'].values.tolist())
            
            if not data_to_write:
                return {
                    "success": False,
                    "error": "No data to write",
                    "message": "Results do not contain data to export"
                }
            
            # Write to sheet
            body = {
                'values': data_to_write
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body=body
            ).execute()
            
            return {
                "success": True,
                "updated_cells": result.get('updates', {}).get('updatedRows', 0),
                "message": f"Successfully wrote results to '{sheet_name}'"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to write results: {str(e)}"
            }
    
    def create_analysis_sheet(
        self,
        question: str,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new sheet with analysis results.
        
        Args:
            question: The analysis question
            results: Analysis results
        
        Returns:
            Creation status
        """
        if not self.is_authenticated or not self.spreadsheet_id:
            return {
                "success": False,
                "error": "Not authenticated or no spreadsheet selected",
                "message": "Please authenticate and select a spreadsheet first"
            }
        
        try:
            # Create new sheet
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': 'Analysis'
                        }
                    }
                }]
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=request_body
            ).execute()
            
            # Write analysis summary
            summary_data = [
                ["Analysis Summary"],
                ["Question", question],
                ["Agent", results.get('selected_agent', 'N/A')],
                ["Validation", "Passed" if results.get('valid') else "Failed"],
                [],
                ["Insights"]
            ]
            
            if results.get('insights'):
                for insight in results['insights']:
                    summary_data.append([insight])
            
            body = {
                'values': summary_data
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range="Analysis!A1",
                valueInputOption="RAW",
                body=body
            ).execute()
            
            return {
                "success": True,
                "message": "Created analysis sheet with summary"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create analysis sheet: {str(e)}"
            }
    
    def close(self):
        """Cleanup resources"""
        self.service = None
        self.spreadsheet_id = None
        self.is_authenticated = False
