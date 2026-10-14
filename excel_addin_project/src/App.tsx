
// App.tsx - Main React component

import React, { useState, useEffect } from 'react';
import { getExcelData, writeResultsToExcel, createChart, createSummarySheet } from './main';

const App: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const analyzeData = async () => {
    setLoading(true);
    setError('');
    
    try {
      // Get data from Excel
      const excelData = await getExcelData();
      
      // Send to backend API
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: question,
          data: excelData
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setResults(data.results);
        
        // Write results back to Excel
        await writeResultsToExcel(data.results, 'A10');
        
        // Create chart if applicable
        if (data.chart_data) {
          await createChart('A10', 'ColumnClustered');
        }
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError('Analysis failed: ' + (err as Error).message);
    }
    
    setLoading(false);
  };

  return (
    <div className="taskpane">
      <h1>Multi-Agent Data Analyst</h1>
      
      <div className="input-section">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your data..."
          rows={3}
        />
        <button onClick={analyzeData} disabled={loading}>
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>
      
      {error && <div className="error">{error}</div>}
      
      {results.length > 0 && (
        <div className="results">
          <h2>Results</h2>
          <table>
            {results.map((row, i) => (
              <tr key={i}>
                {row.map((cell: any, j: number) => (
                  <td key={j}>{cell}</td>
                ))}
              </tr>
            ))}
          </table>
        </div>
      )}
    </div>
  );
};

export default App;
