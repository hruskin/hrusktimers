"""
Platform for splitting Google Home timers into individual sensors.

For more details about this platform, please refer to the documentation at
https://www.home-assistant.io/integrations/sensor/
"""
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (
    EVENT_HOMEASSISTANT_START,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.event import async_track_state_change_event
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

DOMAIN = "google_timer_splitter"
CONF_SOURCE = "source"
NUM_TIMER_SENSORS = 4

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_SOURCE): cv.entity_id,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Google Timer Splitter sensor platform."""
    source_entity_id = config[CONF_SOURCE]

    sensors = [
        GoogleTimerSplitterSensor(hass, source_entity_id, i)
        for i in range(NUM_TIMER_SENSORS)
    ]

    async_add_entities(sensors)

    @callback
    def _update_sensors(event: Event | None = None) -> None:
        """Update all sensors based on the source entity's state."""
        source_state = hass.states.get(source_entity_id)
        timers_data = []

        if source_state and source_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            timers_attr = source_state.attributes.get("timers")
            if isinstance(timers_attr, list):
                timers_data = timers_attr
            elif timers_attr is not None:
                _LOGGER.warning(
                    "The 'timers' attribute of %s is not a list. Got: %s",
                    source_entity_id,
                    timers_attr,
                )
        else:
            _LOGGER.debug("Source entity %s is unavailable.", source_entity_id)

        _LOGGER.debug("Updating timer sensors with data: %s", timers_data)
        for sensor in sensors:
            sensor.update_from_source(timers_data)

    # Listen for changes to the source entity
    async_track_state_change_event(hass, [source_entity_id], _update_sensors)

    # Schedule a call to update sensors once Home Assistant is started.
    # The lambda is used to pass no arguments to _update_sensors.
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, lambda _: _update_sensors())
    
    # Perform an initial update in case the source is already available
    _update_sensors()


class GoogleTimerSplitterSensor(SensorEntity):
    """Representation of a single timer slot sensor."""

    def __init__(
        self, hass: HomeAssistant, source_entity_id: str, slot_index: int
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._source_entity_id = source_entity_id
        self._slot_index = slot_index

        self._attr_name = f"Minutka {self._slot_index + 1}"
        self._attr_unique_id = f"{DOMAIN}_timer_{self._slot_index + 1}"
        self._attr_icon = "mdi:timer-outline"
        self._attr_should_poll = False
        
        # Set initial state
        self._set_idle_state()

    @property
    def available(self) -> bool:
        """Return True if the source entity is available."""
        source_state = self.hass.states.get(self._source_entity_id)
        return source_state is not None

    def _parse_duration_to_seconds(self, duration_str: str) -> int:
        """Parse H:M:S, M:S, or S duration string to seconds."""
        try:
            parts = [int(p) for p in duration_str.split(':')]
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
            if len(parts) == 1:
                return parts[0]
        except (ValueError, IndexError) as ex:
            _LOGGER.warning("Could not parse duration '%s': %s", duration_str, ex)
        return 0

    @callback
    def _set_idle_state(self) -> None:
        """Set the sensor to its idle state."""
        self._attr_native_value = "idle"
        self._attr_extra_state_attributes = {"duration": "0:00:00"}

    @callback
    def update_from_source(self, timers_data: list) -> None:
        """Update the sensor's state and attributes from the source data."""
        if self._slot_index < len(timers_data):
            timer_data = timers_data[self._slot_index]

            if isinstance(timer_data, dict) and timer_data.get("status") == "set":
                fire_time_ts = timer_data.get("fire_time")
                duration_str = timer_data.get("duration", "0:00:00")

                if fire_time_ts:
                    duration_sec = self._parse_duration_to_seconds(duration_str)
                    fire_time_dt = dt_util.utc_from_timestamp(fire_time_ts)
                    start_time_dt = fire_time_dt - timedelta(seconds=duration_sec)
                    remaining_sec = max(0, int((fire_time_dt - dt_util.utcnow()).total_seconds()))

                    self._attr_native_value = "active"
                    self._attr_extra_state_attributes = {
                        "duration": duration_str,
                        "finishing_at": fire_time_dt.isoformat(),
                        "start_time": start_time_dt.isoformat(),
                        "remaining": remaining_sec,
                    }
                    self.async_write_ha_state()
                    return

        # This part is reached if no timer data for the slot, status is not 'set',
        # or data is invalid.
        self._set_idle_state()
        self.async_write_ha_state()
