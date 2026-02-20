# User value: This service gives users clear Hindi next-steps for queued, failed, and cancelled jobs.
from typing import Optional


# User value: builds a consistent assist payload so UI can render reliable guidance actions.
def assist_payload(
    *,
    level: str,
    title: str,
    message: str,
    action_label: str = "",
    action_type: str = "",
) -> dict:
    return {
        "level": str(level or "INFO").upper(),
        "title": str(title or "").strip(),
        "message": str(message or "").strip(),
        "action_label": str(action_label or "").strip(),
        "action_type": str(action_type or "").strip().upper(),
    }


# User value: maps status/error into Hindi guidance so users know the best next action immediately.
def derive_user_assist(
    *,
    status: str,
    error_code: str = "",
    stage: str = "",
    queue_wait_sec: Optional[int] = None,
) -> Optional[dict]:
    state = str(status or "").strip().upper()
    code = str(error_code or "").strip().upper()
    stage_text = str(stage or "").strip()
    wait_sec = int(queue_wait_sec or 0)

    if state == "QUEUED":
        # Agent-6 queue hint is primary for normal queued state; assist appears only on prolonged wait.
        if wait_sec < 90:
            return None
        return assist_payload(
            level="WARN",
            title="कतार में अधिक प्रतीक्षा",
            message="उच्च लोड के कारण आपका कार्य कतार में है। कृपया थोड़ी देर प्रतीक्षा करें या इतिहास से बाद में स्थिति देखें।",
            action_label="इतिहास देखें",
            action_type="OPEN_HISTORY",
        )

    if state == "FAILED":
        if code in {"AUTH_INVALID_TOKEN", "AUTH_UNAUTHORIZED", "AUTH_MISSING_TOKEN"}:
            return assist_payload(
                level="ERROR",
                title="सत्र समाप्त हो गया",
                message="आपका लॉगिन सत्र समाप्त हो गया है। कृपया दोबारा साइन-इन करके पुनः प्रयास करें।",
                action_label="फिर से साइन-इन",
                action_type="RELOGIN",
            )
        if code in {"UNSUPPORTED_MIME_TYPE", "UNSUPPORTED_FILE_TYPE", "MEDIA_DECODE_FAILED"}:
            return assist_payload(
                level="WARN",
                title="फ़ाइल प्रारूप समर्थित नहीं",
                message="यह फ़ाइल पढ़ी नहीं जा सकी। सही प्रकार की फ़ाइल चुनकर पुनः अपलोड करें।",
                action_label="नया अपलोड",
                action_type="REUPLOAD",
            )
        if code in {"INFRA_REDIS", "HTTP_503", "PROCESSING_FAILED"}:
            return assist_payload(
                level="WARN",
                title="अस्थायी तकनीकी समस्या",
                message="सर्वर व्यस्त या अस्थायी रूप से अनुपलब्ध है। कृपया थोड़ी देर बाद पुनः प्रयास करें।",
                action_label="पुनः प्रयास",
                action_type="RETRY_JOB",
            )
        return assist_payload(
            level="WARN",
            title="प्रोसेसिंग असफल रही",
            message=stage_text or "कृपया फ़ाइल जाँचकर पुनः प्रयास करें।",
            action_label="पुनः प्रयास",
            action_type="RETRY_JOB",
        )

    if state == "CANCELLED":
        return assist_payload(
            level="INFO",
            title="कार्य रद्द किया गया",
            message="यह कार्य रद्द हो चुका है। चाहें तो नई फ़ाइल के साथ फिर से शुरू करें।",
            action_label="नया अपलोड",
            action_type="REUPLOAD",
        )

    return None
