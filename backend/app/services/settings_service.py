import httpx

from app.core.config import AppConfig, load_config, save_config
from app.core.errors import ValidationAppError
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest

HEALTH_TIMEOUT_SECONDS = 2


def _normalize_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    if not normalized:
        return normalized
    if "://" not in normalized:
        return "http://" + normalized
    return normalized


def check_usage_service(url: str, management_key: str = "") -> tuple[bool, str | None]:
    base_url = _normalize_base_url(url)
    if not base_url:
        return False, "主统计服务地址未配置"
    try:
        with httpx.Client(base_url=base_url, timeout=HEALTH_TIMEOUT_SECONDS) as client:
            health = client.get("/health")
            if not 200 <= health.status_code < 300:
                return False, f"/health HTTP {health.status_code}"
            headers = {"Authorization": f"Bearer {management_key}"} if management_key else {}
            status = client.get("/status", headers=headers)
            if status.status_code == 401:
                return False, "/status 管理密钥无效"
            if status.status_code == 412:
                return False, "/status 主统计服务未配置"
            if not 200 <= status.status_code < 300:
                return False, f"/status HTTP {status.status_code}"
    except httpx.HTTPError as exc:
        return False, f"{exc.__class__.__name__}: {str(exc)[:160]}"
    return True, None


def settings_to_response(config: AppConfig | None = None) -> SettingsResponse:
    current = config or load_config()
    collector = current.collector
    usage_available, usage_error = check_usage_service(
        current.usage_service_url,
        collector.management_key,
    )
    return SettingsResponse(
        cliaproxy_url=collector.cliaproxy_url,
        usage_service_url=current.usage_service_url,
        usage_service_available=usage_available,
        usage_service_error=usage_error,
        management_key=collector.management_key,
        management_key_set=bool(collector.management_key),
        collector_enabled=collector.enabled,
        queue_name=collector.queue_name,
        batch_size=collector.batch_size,
        poll_interval_seconds=collector.poll_interval_seconds,
        retry_interval_seconds=collector.retry_interval_seconds,
    )


def update_settings(payload: SettingsUpdateRequest) -> SettingsResponse:
    config = load_config()
    collector = config.collector
    if payload.cliaproxy_url is not None:
        collector.cliaproxy_url = _normalize_base_url(payload.cliaproxy_url)
    if payload.usage_service_url is not None:
        config.usage_service_url = _normalize_base_url(payload.usage_service_url)
    if payload.management_key is not None:
        collector.management_key = payload.management_key.strip()
    if payload.collector_enabled is not None:
        collector.enabled = payload.collector_enabled
    if payload.queue_name is not None:
        collector.queue_name = payload.queue_name.strip()
    if payload.batch_size is not None:
        collector.batch_size = payload.batch_size
    if payload.poll_interval_seconds is not None:
        collector.poll_interval_seconds = payload.poll_interval_seconds
    if payload.retry_interval_seconds is not None:
        collector.retry_interval_seconds = payload.retry_interval_seconds
    if collector.enabled:
        usage_available, _ = check_usage_service(config.usage_service_url, collector.management_key)
        if usage_available:
            raise ValidationAppError(
                "主统计服务可用时不能开启本地应急采集；请保持 18318 作为唯一 usage 队列消费者。"
            )
    save_config(config)
    return settings_to_response(config)
