# Excel Add-in Setup Guide

## 🎯 **Quick Start - Office 365 Online (Recommended)**

The easiest way to use the Excel Add-in is through Office 365 Online, which supports sideloading.

### **Step 1: Go to Excel Online**
1. Open browser and go to: https://office.live.com/start/Excel
2. Sign in with your Microsoft account

### **Step 2: Upload the Add-in**
1. In Excel Online, go to **Insert → Office Add-ins**
2. Click **"Upload My Add-in"** or **"Sideload Add-in"**
3. Browse to: `D:\Projects\Project Multi Agent DA\Multi-Agent-Data-Analyst\excel_addin_project\`
4. Select: `manifest.xml`
5. Click **"Upload"**

### **Step 3: Use the Add-in**
1. The Add-in will appear in the ribbon
2. Click "Multi-Agent Data Analyst"
3. Upload your Excel file
4. Ask questions
5. View results

---

## 🖥️ **Excel Desktop Alternative**

### **Option 1: Trust Center Configuration**

1. **Open Excel**
2. **File → Options → Trust Center → Trust Center Settings**
3. **Trusted Add-in Catalogs**
4. **Add:** `http://127.0.0.1:3000`
5. **Check:** "Show in Menu"
6. **OK → OK**

Then try:
- **Insert → Add-ins → Get Add-ins → Managed Admin → Multi-Agent Data Analyst**

### **Option 2: Registry Edit (Advanced)**

1. **Open Registry Editor** (regedit)
2. **Navigate to:** `HKEY_CURRENT_USER\Software\Microsoft\Office\16.0\WEF\Developer`
3. **Create DWORD:** `AllowSideLoad` = 1
4. **Restart Excel**
5. **Insert → Add-ins → Get Add-ins → Upload My Add-in**

---

## 🧪 **Test the Add-in UI First**

Before loading in Excel, test the interface in your browser:

1. **Open:** `excel_addin_project/standalone.html` in your browser
2. **Test the UI** (upload file, ask question)
3. **Verify the interface works**

This confirms the Add-in UI is functional before loading in Excel.

---

## 🔧 **Backend Required**

The Excel Add-in requires the Python backend to be running:

```powershell
cd "D:\Projects\Project Multi Agent DA\Multi-Agent-Data-Analyst"
python app.py
```

The Add-in connects to: `http://localhost:8000/analyze`

---

## 📋 **Current Status**

✅ **Complete:**
- Excel Add-in project generated
- React component built
- TypeScript compiled
- Bundle created (dist/bundle.js)
- HTTP server running (port 3000)
- Manifest configured

⚠️ **Requirements:**
- Office 365 Online account (recommended)
- OR Excel 2016+ with sideloading enabled
- OR Trust Center configuration
- Python backend running

---

## 💡 **Recommendation**

**Use Office 365 Online** - it's the most reliable method for sideloading custom Add-ins during development.

**Alternative:** Use the Streamlit UI at `http://localhost:8501` - it provides the same functionality without Excel integration complexity.
