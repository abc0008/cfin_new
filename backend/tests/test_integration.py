from models.tools import ChartGenerationTool, TableGenerationTool, ToolSchema
from models.visualization import ChartData, TableData, VisualizationData

class TestModelIntegration:
    """Test that our model files can be imported correctly."""
    
    def test_import_tools(self):
        """Test that tool models can be imported."""
        # Create a ToolSchema
        tool = ToolSchema(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}}
        )
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        
        # Create a ChartGenerationTool
        chart_tool = ChartGenerationTool()
        assert chart_tool.name == "generate_graph_data"
        
        # Create a TableGenerationTool
        table_tool = TableGenerationTool()
        assert table_tool.name == "generate_table_data"
    
    def test_import_visualization(self):
        """Test that visualization models can be imported."""
        # Create a ChartData with all required fields
        chart = ChartData(
            chartType="bar",
            config={
                "title": "Test Chart",
                "description": "A test chart description"
            },
            data=[{"x": 1, "y": 2}],
            chartConfig={"y": {"label": "Y Axis"}}
        )
        assert chart.chartType == "bar"
        assert chart.config["description"] == "A test chart description"
        
        # Create a TableData with all required fields
        table = TableData(
            tableType="simple",
            config={
                "title": "Test Table",
                "description": "A test table description",
                "columns": [{"key": "id", "label": "ID"}]
            },
            data=[{"id": 1, "name": "Test"}]
        )
        assert table.tableType == "simple"
        assert table.config["description"] == "A test table description"
        
        # Create a VisualizationData
        viz = VisualizationData(
            charts=[chart],
            tables=[table]
        )
        assert len(viz.charts) == 1
        assert len(viz.tables) == 1 