"""Sensoren voor Ennie laadkosten over de gekozen periode."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN, END_HELPER, START_HELPER, Settings
from .data import async_calculate, read_period

_LOGGER = logging.getLogger(__name__)

SENSORS = (
    ("kwh", "Ennie geladen energie periode", "kWh", "mdi:ev-station"),
    ("cost", "Ennie laadkosten periode", "€", "mdi:currency-eur"),
    ("employer", "Ennie vergoeding periode", "€", "mdi:cash-plus"),
    ("difference", "Ennie verschil periode", "€", "mdi:chart-line"),
    ("average", "Ennie gemiddelde stroomprijs periode", "€/kWh", "mdi:flash"),
    ("missing_kwh", "Ennie kWh zonder prijs periode", "kWh", "mdi:alert-circle-outline"),
    ("solar_kwh", "Ennie zonne-energie periode", "kWh", "mdi:solar-power-variant"),
    ("extern_kwh", "Ennie extern geladen energie periode", "kWh", "mdi:map-marker-radius"),
)


async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    settings: Settings = hass.data[DOMAIN]["settings"]

    async def update() -> dict:
        try:
            from_date, to_date = read_period(hass)
            return await async_calculate(hass, settings, from_date, to_date)
        except Exception as exc:  # noqa: BLE001 - fout zichtbaar maken als attribuut
            _LOGGER.exception("Ennie laadkosten berekening mislukt")
            return {"error": str(exc)}

    # Statistieken veranderen maar één keer per uur; we verversen op :12
    # (ruim na het compileren van de uurstatistiek) en bij een periodewijziging.
    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name="Ennie laadkosten", update_method=update, update_interval=None
    )
    hass.data[DOMAIN]["coordinator"] = coordinator

    @callback
    def _refresh(*_args) -> None:
        hass.async_create_task(coordinator.async_request_refresh())

    @callback
    def _period_changed(event: Event) -> None:
        _refresh()

    unsubs = hass.data[DOMAIN].setdefault("unsub", [])
    unsubs.append(async_track_state_change_event(hass, [START_HELPER, END_HELPER], _period_changed))
    unsubs.append(async_track_time_change(hass, _refresh, minute=12, second=0))
    # Eerste berekening pas als HA (en dus de helpers en de recorder) volledig draait.
    unsubs.append(async_at_started(hass, _refresh))

    async_add_entities(EnnieCostSensor(coordinator, *spec) for spec in SENSORS)


class EnnieCostSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = False

    def __init__(self, coordinator, key, name, unit, icon):
        super().__init__(coordinator)
        self.key = key
        self._attr_name = name
        self._attr_unique_id = f"ennie_laadkosten_{key}_periode"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return None if "error" in data else data.get(self.key)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        if not data:
            return {}
        if "error" in data:
            return {"fout": data["error"]}
        attrs = {
            "periode": data["period"],
            "toelichting": data["note"],
            "prijsdekking_kwh": data["priced_kwh"],
            "zonne_kwh": data["solar_kwh"],
            "extern_kwh": data["extern_kwh"],
            "geschat_verdeeld_kwh": data["estimated_kwh"],
            "ontbrekende_uurreeksen": data["gaps"],
            "genegeerde_onwaarschijnlijke_kwh": data["ignored_kwh"],
            "tariefbron": data["tariefbron"],
            "vergoeding_per_kwh": data["vergoeding_tarieven"],
        }
        if self.key == "cost":
            attrs.update(
                {
                    "dagtotalen": data["daily"],
                    "dagtotalen_afgekapt": data["daily_truncated"],
                    "kwh_zonder_prijs": data["missing_kwh"],
                }
            )
        return attrs
