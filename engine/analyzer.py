import asyncio
from collections import deque
from dataclasses import asdict
from datetime import datetime
from shared_models import Event

from settings.config_loader import config
from log.logger import logger


class Analyzer:
    def __init__(self, pipeline):
        self.pipeline = pipeline        # Чтобы кидать обратно в пайплайн
        self.thresholds = config._data.get("anomaly_thresholds", {}) # два конфига
        self.consecutive_limit = self.thresholds.get("consecutive_hits", 3)
        self.cooldown_seconds = 60  

        self.windows = {}               # Окна для детекта: {source: deque}
        self.alert_states = {}          # Текущий статус: {source: "ACTIVE" | "RESOLVED"}
        self.last_sent_at = {}          # Время последней отправки: {source: timestamp}

    def _get_threshold_key(self, source):
        mapping = {
            "cpu_collector": ("cpu_usage_percent"),
            "ram_collector": ("used_percent", "ram_usage_percent"),
            "disk_collector": ("used_percent", "disk_usage_percent")
        }
        return mapping.get(source)

    async def process_metric(self, event: Event):
        source = event.source
        data = event.data
        
        keys = self._get_threshold_key(source)
        if not keys:
            return

        data_key, threshold_key = keys
        logger.info(f"[ANALYZER] Checking {source} with data key {data_key} and threshold key {threshold_key}. Value: {data.get(data_key)}")
        if data_key not in data:
            return

        limit = self.thresholds.get(threshold_key, 100.0)
        if source not in self.windows:
            self.windows[source] = deque(maxlen=self.consecutive_limit)
        
        self.windows[source].append(data[data_key] >= limit)
        
        is_anomaly = len(self.windows[source]) == self.consecutive_limit and all(self.windows[source])

        await self._handle_alert_logic(source, is_anomaly, event)

    async def _handle_alert_logic(self, source, is_anomaly, original_event):
        now = datetime.now().timestamp()
        current_state = self.alert_states.get(source, "RESOLVED")
        last_send = self.last_sent_at.get(source, 0)

        if is_anomaly:
            logger.info(f"[ANALYZER] Anomaly detected: bool value -> {is_anomaly} with event: {original_event}")
            if current_state == "RESOLVED" or (now - last_send > self.cooldown_seconds):
                state_to_send = "NEW" if current_state == "RESOLVED" else "ACTIVE"
                
                self.alert_states[source] = "ACTIVE"
                self.last_sent_at[source] = now
                await self._emit_alert(source, state_to_send, "critical", original_event.data)

        elif not is_anomaly and current_state == "ACTIVE":
            self.alert_states[source] = "RESOLVED"
            self.last_sent_at[source] = now
            await self._emit_alert(source, "RESOLVED", "info", original_event.data)

    async def _emit_alert(self, source, state, severity, trigger_data):
        msg_map = {
            "NEW": f"CRITICAL: {source} exceeded threshold!",
            "ACTIVE": f"STILL CRITICAL: {source} is under pressure",
            "RESOLVED": f"OK: {source} recovered to normal state"
        }

        alert_event = Event(
            source=source,
            type="alert",
            timestamp=datetime.now().timestamp(),
            data={
                "state": state,
                "severity": severity,
                "message": msg_map.get(state, "Unknown alert state"),
                "trigger_values": trigger_data
            }
        )
        
        await self.pipeline.emit_event(alert_event)
        logger.info(f"[ANALYZER] Alert emitted: {source} -> {state}")