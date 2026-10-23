# 1. Load API key
import os
from dotenv import load_dotenv

load_dotenv()

# 2. Connect LLM
from openai import OpenAI

llm = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# 3. Connect MCP
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server = StdioServerParameters(
        command="python",
        args=["server.py"]
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 4. Discover tools
            mcp_tools = (await session.list_tools()).tools

            tools = [{
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            } for t in mcp_tools]

            # 5. Ask LLM
            messages = [
                {"role": "user", "content": "What is 2 + 3?"}
            ]

            response = llm.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=messages,
                tools=tools,
                tool_choice="required"
            )

            # 6. Execute MCP tool
            msg = response.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))

            for call in msg.tool_calls or []:
                args = json.loads(call.function.arguments)

                result = await session.call_tool(
                    call.function.name, args
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(result.content)
                })

            # 7. Ask LLM for final answer
            final = llm.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=messages
            )

            print(final.choices[0].message.content)

asyncio.run(main())