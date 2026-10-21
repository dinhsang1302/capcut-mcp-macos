"""macOS-only stdio MCP handshake and capcut_probe, no project edits."""
import asyncio
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check():
    executable = Path(sys.executable).with_name('capcut-mcp')
    if not executable.is_file():
        raise FileNotFoundError(executable)
    async with stdio_client(StdioServerParameters(command=str(executable))) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f'MCP handshake OK; {len(tools.tools)} tools.')
            result = await session.call_tool('capcut_probe', {})
            if result.is_error:
                raise RuntimeError(result)
            for block in result.content:
                if block.type == 'text':
                    print(block.text)
            print('No edit/save tool called. Inspect all warnings before using a project.')


if __name__ == '__main__':
    if sys.platform != 'darwin':
        raise SystemExit('Run this check on the actual Mac. No macOS compatibility claim can be made from another OS.')
    asyncio.run(asyncio.wait_for(check(), timeout=90))
