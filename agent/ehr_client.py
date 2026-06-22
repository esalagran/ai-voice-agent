from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel

from ehr_service.rpc import RPCOperation


class EHRClientError(Exception):
    def __init__(self, code: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

    def as_tool_error(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "status_code": self.status_code}


class EHRClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:7861",
        timeout: float = 5.0,
        client: httpx.AsyncClient | None = None,
    ):
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def check_health(self) -> None:
        try:
            response = await self._client.get("/health")
        except (httpx.TimeoutException, httpx.RequestError) as error:
            raise EHRClientError("ehr_unavailable", "EHR service is unavailable") from error
        if response.status_code >= 400:
            raise EHRClientError("ehr_unavailable", "EHR service is unavailable", response.status_code)

    async def call(
        self, operation: RPCOperation, request: BaseModel
    ) -> BaseModel | list[BaseModel] | None:
        data = await self._post(operation, request)
        if data is None and operation.returns_none:
            return None
        if operation.returns_list:
            return [operation.response_model.model_validate(item) for item in data]
        return operation.response_model.model_validate(data)

    async def _post(self, operation: RPCOperation, request: BaseModel) -> Any:
        try:
            response = await self._client.post(
                operation.path,
                json=request.model_dump(mode="json"),
            )
        except (httpx.TimeoutException, httpx.RequestError) as error:
            raise EHRClientError("ehr_unavailable", "EHR service is unavailable") from error

        if response.status_code >= 400:
            raise EHRClientError(
                self._error_code(response.status_code),
                self._error_message(response),
                response.status_code,
            )

        return response.json()

    def _error_code(self, status_code: int) -> str:
        return {
            400: "validation_error",
            404: "not_found",
            409: "conflict",
        }.get(status_code, "ehr_error")

    def _error_message(self, response: httpx.Response) -> str:
        try:
            detail = response.json().get("detail")
        except ValueError:
            detail = None
        return str(detail or "EHR request failed")
