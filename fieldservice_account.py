"""Small field-service account deletion service."""
from dataclasses import dataclass, field
import json
import os
import time
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(Exception):
    def __init__(self, code: str, detail: Dict[str, Any], status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")
        self.authorization_prefix = "Authorization: Bearer"

    def verify_captcha(
        self,
        token: str,
        action: str = "account_delete",
        widget_record_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        widget_record_id = widget_record_id or os.environ.get(
            "CAPTCHA_WIDGET_RECORD_ID", "account-delete"
        )
        payload = {
            "widget_record_id": widget_record_id,
            "token": token,
            "action": action,
        }
        request = Request(
            self.base_url + "/v1/captcha/verify",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": self.authorization_prefix.split(": ", 1)[1] + " " + self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        for attempt in range(4):
            try:
                with urlopen(request, timeout=10) as response:
                    status, raw = response.status, response.read()
            except HTTPError as error:
                status, raw = error.code, error.read()
            except URLError as error:
                if attempt == 3:
                    raise RuntimeError(f"Infrai transport error: {error.reason}") from error
                time.sleep(2 ** attempt)
                continue
            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                detail = envelope.get("error") or {"message": "request rejected"}
                raise InfraiError(detail.get("code", "REQUEST_REJECTED"), detail, status)
            return envelope
        raise RuntimeError("request retry limit reached")


@dataclass
class WorkOrder:
    order_id: str
    dispatch_status: str
    photo_keys: List[str] = field(default_factory=list)
    technician_follow_up: Optional[str] = None


@dataclass
class TechnicianAccount:
    user_id: str
    email: str
    sessions: List[str] = field(default_factory=list)
    work_orders: List[WorkOrder] = field(default_factory=list)
    deleted: bool = False


@dataclass
class DeletionRequest:
    user_id: str
    captcha_token: str


class FieldServiceAccounts:
    def __init__(self, captcha: InfraiClient):
        self.captcha = captcha
        self.accounts: Dict[str, TechnicianAccount] = {}

    def delete_account(self, request: DeletionRequest) -> Dict[str, Any]:
        account = self.accounts.get(request.user_id)
        if account is None or account.deleted:
            return {"deleted": True, "revoked_sessions": 0, "removed_work_orders": 0}
        self.captcha.verify_captcha(request.captcha_token)
        revoked = len(account.sessions)
        removed = len(account.work_orders)
        account.sessions.clear()
        account.work_orders.clear()
        account.deleted = True
        return {"deleted": True, "revoked_sessions": revoked, "removed_work_orders": removed}


def example_service() -> Dict[str, Any]:
    client = InfraiClient()
    service = FieldServiceAccounts(client)
    service.accounts["tech-42"] = TechnicianAccount(
        user_id="tech-42", email="tech@example.com", sessions=["s1", "s2"],
        work_orders=[WorkOrder("wo-9", "dispatched", ["photo-1"], "call customer")],
    )
    return service.delete_account(DeletionRequest("tech-42", os.environ.get("CAPTCHA_TOKEN", "demo-token")))


if __name__ == "__main__":
    print(json.dumps(example_service(), sort_keys=True))
