from __future__ import annotations

from inspect import signature
from typing import Any, Type

from src.agent.config import Settings
from src.agent.tools.base import BaseTool
from src.agent.tools.cms_coverage import CMSCoverageTool
from src.agent.tools.fixture_retrieval import FixtureRetrievalTool


TOOL_CLASSES: dict[str, Type[BaseTool]] = {
    CMSCoverageTool.name: CMSCoverageTool,
    FixtureRetrievalTool.name: FixtureRetrievalTool,
}


def load_tool(name: str, settings: Settings | None = None) -> BaseTool:
    tool_cls = TOOL_CLASSES.get(name)
    if tool_cls is None:
        raise ValueError(f"Unknown tool: {name}")

    init_sig = signature(tool_cls.__init__)
    if "settings" in init_sig.parameters:
        if settings is None:
            raise ValueError(f"Tool {name} requires a Settings instance")
        return tool_cls(settings=settings)

    return tool_cls()
