"""Ennie laadkosten: historische laadkosten en PDF-declaratie."""
from __future__ import annotations

import logging

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType

from .const import CONFIG_SCHEMA, DOMAIN, Settings  # noqa: F401 - CONFIG_SCHEMA wordt door HA gebruikt
from .data import async_calculate, read_period
from .declaratie import make_pdf

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    settings = Settings.from_config(config.get(DOMAIN))
    hass.data.setdefault(DOMAIN, {})["settings"] = settings

    hass.async_create_task(async_load_platform(hass, "sensor", DOMAIN, {}, config))

    async def ververs(call: ServiceCall) -> None:
        coordinator = hass.data[DOMAIN].get("coordinator")
        if coordinator is not None:
            await coordinator.async_request_refresh()

    async def maak_declaratie(call: ServiceCall) -> ServiceResponse:
        try:
            from_date, to_date = read_period(hass)
            data = await async_calculate(hass, settings, from_date, to_date)
            output_dir = hass.config.path("www", "declaraties")
            _, url = await hass.async_add_executor_job(
                make_pdf, data, from_date, to_date, output_dir, settings.declarant
            )
            persistent_notification.async_create(
                hass,
                f"De declaratie is aangemaakt voor {from_date:%d-%m-%Y} t/m {to_date:%d-%m-%Y}. "
                f"[Download de PDF]({url})",
                title="Ennie - declaratie gereed",
                notification_id="ennie_declaratie",
            )
            _LOGGER.info("Ennie declaratie opgeslagen: %s", url)
            # De bestandsnaam bevat een willekeurig deel; geef de URL terug
            # zodat de dashboardknop het bestand kan openen.
            return {"url": url} if call.return_response else None
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("Ennie declaratie maken mislukt")
            persistent_notification.async_create(
                hass,
                f"De declaratie kon niet worden gemaakt: {exc}",
                title="Ennie - declaratie mislukt",
                notification_id="ennie_declaratie",
            )
            if call.return_response:
                raise HomeAssistantError(f"De declaratie kon niet worden gemaakt: {exc}") from exc
            return None

    hass.services.async_register(DOMAIN, "ververs", ververs)
    hass.services.async_register(
        DOMAIN, "maak_declaratie", maak_declaratie, supports_response=SupportsResponse.OPTIONAL
    )
    return True
