from __future__ import annotations

from typing import Any

from app.core.errors import AppException, SEMANTIC_LOCATOR_FAILED, UI_AUTOMATION_FAILED


class Uiautomator2Adapter:
    def __init__(self) -> None:
        try:
            import uiautomator2 as u2  # type: ignore
        except Exception as exc:
            self.u2 = None
            self.import_error = str(exc)
        else:
            self.u2 = u2
            self.import_error = ""

    def is_available(self) -> bool:
        return self.u2 is not None

    def execute_semantic(self, serial: str, action: str, selector: dict[str, Any], params: dict[str, Any], timeout_sec: int) -> dict[str, Any]:
        if self.u2 is None:
            raise AppException(
                UI_AUTOMATION_FAILED,
                f"uiautomator2 dependency unavailable: {self.import_error or 'not installed'}",
                400,
            )
        try:
            device = self.u2.connect(serial)
            query = self._build_query(selector)
            element = device(**query)
            if not element.exists(timeout=timeout_sec):
                raise AppException(SEMANTIC_LOCATOR_FAILED, "selector did not match any UI element", 400)
            if action == "semantic_click":
                element.click()
            elif action == "semantic_input":
                element.set_text(str(params.get("text", "")))
            elif action == "semantic_assert":
                return {"matched": True, "selector": selector}
            else:
                raise AppException(UI_AUTOMATION_FAILED, f"unsupported semantic action: {action}", 400)
            return {"matched": True, "selector": selector}
        except AppException:
            raise
        except Exception as exc:
            raise AppException(UI_AUTOMATION_FAILED, f"uiautomator2 execution failed: {exc}", 400) from exc

    def _build_query(self, selector: dict[str, Any]) -> dict[str, Any]:
        mapping = {
            "resource_id": "resourceId",
            "resourceId": "resourceId",
            "text": "text",
            "description": "description",
            "class_name": "className",
            "className": "className",
        }
        query = {target: selector[source] for source, target in mapping.items() if selector.get(source)}
        if not query and selector.get("xpath"):
            raise AppException(UI_AUTOMATION_FAILED, "xpath selector is not supported by P0 uiautomator2 adapter", 400)
        if not query:
            raise AppException(SEMANTIC_LOCATOR_FAILED, "selector lacks supported semantic fields", 400)
        return query
