class ToolExecutor:
    """Simple executor for tool callables.

    This replaces the removed langgraph.prebuilt.tool_executor.ToolExecutor.
    It stores a mapping of tool name to callable and executes the tool with
    provided keyword arguments.
    """

    def __init__(self, tools):
        self.tools = {}
        for tool in tools:
            name = getattr(tool, "name", getattr(tool, "__name__", None))
            if not name:
                raise ValueError("Tool must have a name")
            self.tools[name] = tool

    def execute(self, name, args=None):
        if args is None:
            args = {}
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found")
        return self.tools[name](**args)
