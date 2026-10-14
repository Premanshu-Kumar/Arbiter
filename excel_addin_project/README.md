# Excel Add-in for Multi-Agent Data Analyst

This is a complete Excel Add-in project for the Multi-Agent Data Analyst system.

## 📁 Project Structure

```
excel_addin_project/
├── manifest.xml          # Office Add-in manifest
├── package.json          # Node.js dependencies
├── taskpane.html         # Add-in HTML interface
└── src/
    ├── main.ts          # Office.js entry point
    └── App.tsx          # React component
```

## 🚀 Setup Instructions

### Prerequisites

1. **Node.js** (v16 or higher)
   - Download from: https://nodejs.org/
   - Verify installation: `node --version`

2. **npm** (comes with Node.js)
   - Verify installation: `npm --version`

3. **TypeScript**
   - Install globally: `npm install -g typescript`

### Installation Steps

1. **Navigate to the project directory:**
   ```bash
   cd excel_addin_project
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Install additional required packages:**
   ```bash
   npm install react react-dom @types/react @types/react-dom
   npm install office-js
   npm install webpack webpack-cli ts-loader
   npm install --save-dev @types/office-js
   ```

### Build the Project

1. **Initialize TypeScript:**
   ```bash
   npx tsc --init
   ```

2. **Build the project:**
   ```bash
   npm run build
   ```

## 📋 How to Use the Excel Add-in

### Method 1: Sideload in Excel (Development)

1. **Start a local server:**
   ```bash
   npx http-server . -p 3000
   ```

2. **Open Excel:**
   - Launch Microsoft Excel
   - Go to File → Options → Add-ins
   - Select "COM Add-ins" and click "Manage"
   - Click "Add" and select the `manifest.xml` file

3. **Use the Add-in:**
   - Look for "Multi-Agent Data Analyst" in the Excel ribbon
   - Click "Open Analyst" to open the task pane
   - Select data in your Excel sheet
   - Ask questions about your data
   - View results in the task pane

### Method 2: Upload to Microsoft Store (Production)

To distribute the Add-in through the Microsoft Store:

1. **Create a Microsoft Developer account**
   - Sign up at: https://developer.microsoft.com/
   - Register for the Office Store

2. **Package the Add-in:**
   - Build the production version
   - Test thoroughly
   - Submit to Microsoft for review

3. **Distribute:**
   - Once approved, users can find and install from the Office Store

## 🔧 Backend Integration

The Excel Add-in communicates with the Python backend via REST API.

### Backend API Endpoints

The Add-in expects these endpoints:

```python
# Analyze data
POST http://localhost:8000/analyze
Content-Type: application/json

{
  "question": "What is the average value?",
  "data": [[...]]  # Excel data as 2D array
}

# Response
{
  "success": true,
  "results": [[...]],
  "insights": [...],
  "charts": [...]
}
```

### Start the Backend

In the main project directory:

```bash
cd ../Multi-Agent-Data-Analyst
python app.py
```

This starts the Streamlit server at `http://localhost:8501`

## 🎯 Features

The Excel Add-in provides:

- **Direct Excel Integration**: Analyze data without leaving Excel
- **Natural Language Queries**: Ask questions in plain English
- **Multi-Agent Analysis**: Uses Jev + LLM + LangGraph
- **Real-time Results**: View results directly in Excel
- **Chart Generation**: Automatic visualizations
- **Report Export**: Export reports to Excel cells

## 🐛 Troubleshooting

### Add-in doesn't appear in Excel

1. Check if manifest.xml is properly loaded
2. Verify the local server is running on port 3000
3. Check Excel's add-in management settings

### Backend connection fails

1. Ensure the Python backend is running
2. Check CORS settings
3. Verify the API endpoint URL

### Build errors

1. Clear node_modules: `rm -rf node_modules`
2. Reinstall: `npm install`
3. Check TypeScript version compatibility

## 📚 Additional Resources

- [Office.js Documentation](https://docs.microsoft.com/office/dev/add-ins/overview/office-js-overview)
- [Excel Add-in Tutorial](https://docs.microsoft.com/office/dev/add-ins/tutorials/excel-tutorial)
- [React with Office.js](https://docs.microsoft.com/office/dev/add-ins/quickstarts/excel-quickstart-react)

## 🔄 Development Workflow

1. Make changes to TypeScript/React files
2. Run `npm run build`
3. Reload the Add-in in Excel
4. Test the changes

## 📝 Notes

- The Add-in uses the existing Python backend
- All analysis happens on the server (not in Excel)
- Excel is used only for data input and result display
- The Add-in maintains security by not executing code in Excel

## 🎉 Next Steps

1. Set up the development environment
2. Install dependencies
3. Build the project
4. Sideload in Excel for testing
5. Integrate with the Python backend
6. Test end-to-end workflow
