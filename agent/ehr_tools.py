from __future__ import annotations

from typing import Any

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.openai.llm import OpenAILLMService
from pydantic import BaseModel, ValidationError

from agent.ehr_client import EHRClient, EHRClientError
from ehr_service.rpc import RPC_OPERATIONS, RPCOperation


class EHRToolset:
    def __init__(self, client: EHRClient):
        self._client = client
        self._operations = {operation.name: operation for operation in RPC_OPERATIONS}

    @property
    def tools(self) -> ToolsSchema:
        return ToolsSchema([self._function_schema(operation) for operation in RPC_OPERATIONS])

    def register(self, llm: OpenAILLMService) -> None:
        for operation in RPC_OPERATIONS:
            llm.register_function(operation.name, self._handle_tool_call)

    async def _handle_tool_call(self, params: FunctionCallParams) -> None:
        operation = self._operations[params.function_name]
        try:
            request = operation.request_model.model_validate(params.arguments)
            data = self._json_data(await self._client.call(operation, request))
            result = {"ok": True, "data": data}
            if operation.name == "list_availability_slots" and data == []:
                result["message"] = "There are no available slots for that date range."
        except EHRClientError as error:
            result = {"ok": False, "error": error.as_tool_error()}
        except ValidationError as error:
            result = {
                "ok": False,
                "error": {
                    "code": "validation_error",
                    "message": error.errors()[0]["msg"],
                    "status_code": 400,
                },
            }
        await params.result_callback(result)

    def _function_schema(self, operation: RPCOperation) -> FunctionSchema:
        schema = operation.request_schema
        return FunctionSchema(
            name=operation.name,
            description=operation.description,
            properties=schema["properties"],
            required=schema["required"],
        )

    def _json_data(self, data: Any) -> Any:
        if isinstance(data, BaseModel):
            return data.model_dump(mode="json")
        if isinstance(data, list):
            return [self._json_data(item) for item in data]
        return data
