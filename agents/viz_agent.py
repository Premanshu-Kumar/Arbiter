"""
Visualization Agent - Generates Plotly charts
"""
from typing import Dict, Any
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json


class VizAgent:
    """Generates visualizations using Plotly"""
    
    def __init__(self):
        self.supported_charts = {
            "line_chart": self._create_line_chart,
            "bar_chart": self._create_bar_chart,
            "scatter_plot": self._create_scatter_plot,
            "histogram": self._create_histogram,
            "pie_chart": self._create_pie_chart,
            "box_plot": self._create_box_plot,
            "table": self._create_table
        }
    
    def generate_chart(
        self,
        data: pd.DataFrame,
        chart_type: str,
        plan: Dict[str, Any],
        question: str
    ) -> Dict[str, Any]:
        """
        Generate a visualization based on data and plan
        
        Args:
            data: DataFrame with analysis results
            chart_type: Type of chart to generate
            plan: Analysis plan with metadata
            question: Original user question
        
        Returns:
            Chart configuration and metadata
        """
        try:
            if chart_type not in self.supported_charts:
                chart_type = "bar_chart"  # Default fallback
            
            chart_func = self.supported_charts[chart_type]
            fig = chart_func(data, plan, question)
            
            # Convert to JSON for storage
            chart_json = fig.to_json()
            
            return {
                "success": True,
                "chart_type": chart_type,
                "chart_json": chart_json,
                "fig": fig,
                "reasoning": f"Generated {chart_type} successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "chart_type": chart_type,
                "error": str(e),
                "reasoning": f"Chart generation failed: {str(e)}"
            }
    
    def _create_line_chart(
        self,
        data: pd.DataFrame,
        plan: Dict[str, Any],
        question: str
    ) -> go.Figure:
        """Create a line chart for time series data"""
        # Try to identify x and y columns
        x_col = self._find_date_column(data)
        y_col = self._find_numeric_column(data)
        
        if not x_col or not y_col:
            # Use first two columns as fallback
            cols = data.columns.tolist()
            x_col = cols[0]
            y_col = cols[1] if len(cols) > 1 else cols[0]
        
        fig = px.line(
            data,
            x=x_col,
            y=y_col,
            title=question,
            labels={x_col: x_col.replace('_', ' ').title(), 
                   y_col: y_col.replace('_', ' ').title()}
        )
        
        fig.update_layout(
            hovermode='x unified',
            showlegend=True
        )
        
        return fig
    
    def _create_bar_chart(
        self,
        data: pd.DataFrame,
        plan: Dict[str, Any],
        question: str
    ) -> go.Figure:
        """Create a bar chart for categorical comparisons"""
        # Try to identify categorical and numeric columns
        cat_col = self._find_categorical_column(data)
        num_col = self._find_numeric_column(data)
        
        if not cat_col or not num_col:
            # Use first two columns as fallback
            cols = data.columns.tolist()
            cat_col = cols[0]
            num_col = cols[1] if len(cols) > 1 else cols[0]
        
        fig = px.bar(
            data,
            x=cat_col,
            y=num_col,
            title=question,
            labels={cat_col: cat_col.replace('_', ' ').title(),
                   num_col: num_col.replace('_', ' ').title()}
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            showlegend=False
        )
        
        return fig
    
    def _create_scatter_plot(
        self,
        data: pd.DataFrame,
        plan: Dict[str, Any],
        question: str
    ) -> go.Figure:
        """Create a scatter plot for relationships"""
        # Find two numeric columns
        num_cols = self._find_numeric_columns(data, min_count=2)
        
        if len(num_cols) >= 2:
            x_col, y_col = num_cols[0], num_cols[1]
        else:
            cols = data.columns.tolist()
            x_col = cols[0]
            y_col = cols[1] if len(cols) > 1 else cols[0]
        
        fig = px.scatter(
            data,
            x=x_col,
            y=y_col,
            title=question,
            labels={x_col: x_col.replace('_', ' ').title(),
                   y_col: y_col.replace('_', ' ').title()}
        )
        
        return fig
    
    def _create_histogram(
        self,
        data: pd.DataFrame,
        plan: Dict[str, Any],
        question: str
    ) -> go.Figure:
        """Create a histogram for distributions"""
        num_col = self._find_numeric_column(data)
        
        if not num_col:
            num_col = data.columns[0]
        
        fig = px.histogram(
            data,
            x=num_col,
            title=question,
            labels={num_col: num_col.replace('_', ' ').title()}
        )
        
        return fig
    
    def _create_pie_chart(
        self,
        data: pd.DataFrame,
        plan: Dict[str, Any],
        question: str
    ) -> go.Figure:
        """Create a pie chart for part-to-whole relationships"""
        cat_col = self._find_categorical_column(data)
        num_col = self._find_numeric_column(data)
        
        if not cat_col or not num_col:
            cols = data.columns.tolist()
            cat_col = cols[0]
            num_col = cols[1] if len(cols) > 1 else cols[0]
        
        # Limit to top 10 categories for readability
        if len(data) > 10:
            data = data.nlargest(10, num_col)
        
        fig = px.pie(
            data,
            values=num_col,
            names=cat_col,
            title=question,
            labels={cat_col: cat_col.replace('_', ' ').title()}
        )
        
        return fig
    
    def _create_box_plot(
        self,
        data: pd.DataFrame,
        plan: Dict[str, Any],
        question: str
    ) -> go.Figure:
        """Create a box plot for statistical distributions"""
        cat_col = self._find_categorical_column(data)
        num_col = self._find_numeric_column(data)
        
        if not cat_col:
            # Single box plot
            num_col = self._find_numeric_column(data) or data.columns[0]
            fig = px.box(data, y=num_col, title=question)
        else:
            # Grouped box plot
            num_col = self._find_numeric_column(data) or data.columns[1]
            fig = px.box(
                data,
                x=cat_col,
                y=num_col,
                title=question
            )
        
        return fig
    
    def _create_table(
        self,
        data: pd.DataFrame,
        plan: Dict[str, Any],
        question: str
    ) -> go.Figure:
        """Create a table visualization"""
        # Limit to first 20 rows for display
        display_data = data.head(20)
        
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=[col.replace('_', ' ').title() for col in display_data.columns],
                fill_color='paleturquoise',
                align='left',
                font=dict(size=12)
            ),
            cells=dict(
                values=[display_data[col] for col in display_data.columns],
                fill_color='lavender',
                align='left',
                font=dict(size=11)
            )
        )])
        
        fig.update_layout(title=question)
        
        return fig
    
    def _find_date_column(self, data: pd.DataFrame) -> str:
        """Find a date/time column in the DataFrame"""
        for col in data.columns:
            if data[col].dtype == 'datetime64[ns]' or 'date' in col.lower() or 'time' in col.lower():
                return col
        return None
    
    def _find_numeric_column(self, data: pd.DataFrame) -> str:
        """Find a numeric column in the DataFrame"""
        for col in data.columns:
            if pd.api.types.is_numeric_dtype(data[col]):
                return col
        return None
    
    def _find_numeric_columns(self, data: pd.DataFrame, min_count: int = 1) -> list:
        """Find multiple numeric columns in the DataFrame"""
        numeric_cols = []
        for col in data.columns:
            if pd.api.types.is_numeric_dtype(data[col]):
                numeric_cols.append(col)
        return numeric_cols
    
    def _find_categorical_column(self, data: pd.DataFrame) -> str:
        """Find a categorical column in the DataFrame"""
        for col in data.columns:
            if not pd.api.types.is_numeric_dtype(data[col]) and data[col].nunique() < 50:
                return col
        return None
    
    def suggest_chart_type(self, data: pd.DataFrame, question: str) -> str:
        """Suggest the best chart type based on data and question"""
        question_lower = question.lower()
        
        # Time series
        if any(keyword in question_lower for keyword in ["trend", "over time", "change", "growth"]):
            return "line_chart"
        
        # Comparisons
        if any(keyword in question_lower for keyword in ["compare", "top", "bottom", "highest", "lowest"]):
            return "bar_chart"
        
        # Distributions
        if any(keyword in question_lower for keyword in ["distribution", "spread", "range"]):
            return "histogram"
        
        # Relationships
        if any(keyword in question_lower for keyword in ["relationship", "correlation", "vs"]):
            return "scatter_plot"
        
        # Proportions
        if any(keyword in question_lower for keyword in ["proportion", "percentage", "share"]):
            return "pie_chart"
        
        # Default based on data characteristics
        if self._find_date_column(data):
            return "line_chart"
        elif self._find_categorical_column(data):
            return "bar_chart"
        else:
            return "table"
    
    def save_chart(self, fig: go.Figure, file_path: str, format: str = "html") -> bool:
        """Save chart to file"""
        try:
            if format == "html":
                fig.write_html(file_path)
            elif format == "png":
                fig.write_image(file_path)
            elif format == "json":
                with open(file_path, 'w') as f:
                    f.write(fig.to_json())
            return True
        except Exception as e:
            print(f"Error saving chart: {str(e)}")
            return False
