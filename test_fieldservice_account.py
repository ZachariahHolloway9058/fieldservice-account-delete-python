from fieldservice_account import DeletionRequest, FieldServiceAccounts, TechnicianAccount, WorkOrder


class FakeCaptcha:
    def __init__(self):
        self.tokens = []

    def verify_captcha(self, token):
        self.tokens.append(token)
        return {"ok": True, "data": {}}


def test_delete_revokes_every_session_and_removes_field_data():
    captcha = FakeCaptcha()
    service = FieldServiceAccounts(captcha)
    service.accounts["tech-1"] = TechnicianAccount(
        "tech-1", "a@example.com", ["session-a", "session-b"],
        [WorkOrder("wo-1", "en_route", ["photo-x"], "confirm arrival")],
    )
    result = service.delete_account(DeletionRequest("tech-1", "captcha-ok"))
    assert result == {"deleted": True, "revoked_sessions": 2, "removed_work_orders": 1}
    assert service.accounts["tech-1"].sessions == []
    assert service.accounts["tech-1"].work_orders == []
    assert captcha.tokens == ["captcha-ok"]
