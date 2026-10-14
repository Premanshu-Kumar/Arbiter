// main.ts - Main Office.js application

import * as React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

Office.onReady((info) => {
  if (info.host === Office.HostType.Excel) {
    const container = document.getElementById('container');
    if (container) {
      const root = createRoot(container);
      root.render(React.createElement(App));
    }
  }
});

// Excel API functions
export async function getExcelData(): Promise<any[][]> {
  return Excel.run(async (context) => {
    const sheet = context.workbook.worksheets.getActiveWorksheet();
    const range = sheet.getUsedRange();
    range.load('values');
    await context.sync();
    return range.values;
  });
}

export async function writeResultsToExcel(results: any[][], startCell: string = 'A1'): Promise<void> {
  return Excel.run(async (context) => {
    const sheet = context.workbook.worksheets.getActiveWorksheet();
    const range = sheet.getRange(startCell);
    range.values = results;
    await context.sync();
  });
}

export async function createChart(dataRange: string, chartType: any = 'ColumnClustered'): Promise<void> {
  return Excel.run(async (context) => {
    const sheet = context.workbook.worksheets.getActiveWorksheet();
    const range = sheet.getRange(dataRange);
    const chart = sheet.charts.add(chartType, range);
    chart.title.text = 'Analysis Results';
    await context.sync();
  });
}

export async function createSummarySheet(): Promise<void> {
  return Excel.run(async (context) => {
    const sheet = context.workbook.worksheets.add('Analysis Summary');
    sheet.activate();
    await context.sync();
  });
}
