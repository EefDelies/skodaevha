"""Constanten en configuratie voor Ennie laadkosten."""
from __future__ import annotations

from dataclasses import dataclass

import voluptuous as vol

from homeassistant.helpers import config_validation as cv

DOMAIN = "ennie_laadkosten"

START_HELPER = "input_datetime.ennie_kosten_van"
END_HELPER = "input_datetime.ennie_kosten_tot"

# Standaardbronnen; per installatie te overschrijven in configuration.yaml.
DEFAULT_METER = "sensor.oprit_zaptec_go2_meterwaarde"
DEFAULT_PRICE = "sensor.nord_pool_nl_huidige_prijs"
DEFAULT_SOLAR = "sensor.ennie_zonne_laadenergie"
# Extern (niet thuis) geladen energie: alleen getoond, telt nergens mee.
DEFAULT_EXTERN = "sensor.ennie_extern_geladen_energie"
# Tarieven (excl. btw): de helpers zijn de bron. De sensoren spiegelen ze met
# state_class measurement, zodat HA per uur bewaart welk tarief er gold.
DEFAULT_TAX_HELPER = "input_number.ennie_energiebelasting"
DEFAULT_SURCHARGE_HELPER = "input_number.ennie_inkoopvergoeding"
DEFAULT_TAX_SENSOR = "sensor.ennie_tarief_energiebelasting"
DEFAULT_SURCHARGE_SENSOR = "sensor.ennie_tarief_inkoopvergoeding"
DEFAULT_EMPLOYER_HELPER = "input_number.ennie_vergoeding_werkgever"
DEFAULT_EMPLOYER_SENSOR = "sensor.ennie_tarief_vergoeding_werkgever"

# Alleen gebruikt als de helper voor de werkgeversvergoeding ontbreekt.
DEFAULT_EMPLOYER_RATE = 0.35
DEFAULT_VAT = 0.21

# Fysieke bovengrens per uur: 22 kW = 3 x 32 A. Alles daarboven is een
# meterfout of een sprong na vervanging, geen laden.
MAX_PLAUSIBLE_KW = 22.0

CONF_METER = "meter"
CONF_PRICE = "prijs"
CONF_SOLAR = "zonne_energie"
CONF_EXTERN = "extern_energie"
CONF_TAX_HELPER = "energiebelasting_helper"
CONF_SURCHARGE_HELPER = "inkoopvergoeding_helper"
CONF_TAX_SENSOR = "energiebelasting_sensor"
CONF_SURCHARGE_SENSOR = "inkoopvergoeding_sensor"
CONF_EMPLOYER_HELPER = "vergoeding_helper"
CONF_EMPLOYER_SENSOR = "vergoeding_sensor"
CONF_EMPLOYER = "vergoeding_per_kwh"
CONF_VAT = "btw"

# Persoonsgegevens voor de PDF-declaratie. Bewust geen standaardwaarden:
# zet ze in configuration.yaml, bij voorkeur via !secret.
CONF_DECLARATIE = "declaratie"
CONF_DECL_NAAM = "naam"
CONF_DECL_BRON = "bron"
CONF_DECL_IBAN = "iban"
CONF_DECL_REKENINGHOUDER = "rekeninghouder"

DECLARATIE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DECL_NAAM, default=""): cv.string,
        vol.Optional(CONF_DECL_BRON, default=""): cv.string,
        vol.Optional(CONF_DECL_IBAN, default=""): cv.string,
        vol.Optional(CONF_DECL_REKENINGHOUDER, default=""): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Any(
            None,
            vol.Schema(
                {
                    vol.Optional(CONF_METER, default=DEFAULT_METER): cv.entity_id,
                    vol.Optional(CONF_PRICE, default=DEFAULT_PRICE): cv.entity_id,
                    vol.Optional(CONF_SOLAR, default=DEFAULT_SOLAR): cv.entity_id,
                    vol.Optional(CONF_EXTERN, default=DEFAULT_EXTERN): cv.entity_id,
                    vol.Optional(CONF_TAX_HELPER, default=DEFAULT_TAX_HELPER): cv.entity_id,
                    vol.Optional(CONF_SURCHARGE_HELPER, default=DEFAULT_SURCHARGE_HELPER): cv.entity_id,
                    vol.Optional(CONF_TAX_SENSOR, default=DEFAULT_TAX_SENSOR): cv.entity_id,
                    vol.Optional(CONF_SURCHARGE_SENSOR, default=DEFAULT_SURCHARGE_SENSOR): cv.entity_id,
                    vol.Optional(CONF_EMPLOYER_HELPER, default=DEFAULT_EMPLOYER_HELPER): cv.entity_id,
                    vol.Optional(CONF_EMPLOYER_SENSOR, default=DEFAULT_EMPLOYER_SENSOR): cv.entity_id,
                    vol.Optional(CONF_EMPLOYER, default=DEFAULT_EMPLOYER_RATE): vol.Coerce(float),
                    vol.Optional(CONF_VAT, default=DEFAULT_VAT): vol.Coerce(float),
                    vol.Optional(CONF_DECLARATIE, default={}): DECLARATIE_SCHEMA,
                }
            ),
        )
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass(frozen=True)
class Declarant:
    naam: str = ""
    bron: str = ""
    iban: str = ""
    rekeninghouder: str = ""

    @classmethod
    def from_config(cls, conf: dict | None) -> "Declarant":
        conf = conf or {}
        return cls(
            naam=conf.get(CONF_DECL_NAAM, ""),
            bron=conf.get(CONF_DECL_BRON, ""),
            iban=conf.get(CONF_DECL_IBAN, ""),
            rekeninghouder=conf.get(CONF_DECL_REKENINGHOUDER, ""),
        )


@dataclass(frozen=True)
class Settings:
    meter: str
    price: str
    solar: str
    extern: str
    tax_helper: str
    surcharge_helper: str
    tax_sensor: str
    surcharge_sensor: str
    employer_helper: str
    employer_sensor: str
    employer_rate: float
    vat: float
    declarant: Declarant = Declarant()

    @classmethod
    def from_config(cls, conf: dict | None) -> "Settings":
        conf = conf or {}
        return cls(
            meter=conf.get(CONF_METER, DEFAULT_METER),
            price=conf.get(CONF_PRICE, DEFAULT_PRICE),
            solar=conf.get(CONF_SOLAR, DEFAULT_SOLAR),
            extern=conf.get(CONF_EXTERN, DEFAULT_EXTERN),
            tax_helper=conf.get(CONF_TAX_HELPER, DEFAULT_TAX_HELPER),
            surcharge_helper=conf.get(CONF_SURCHARGE_HELPER, DEFAULT_SURCHARGE_HELPER),
            tax_sensor=conf.get(CONF_TAX_SENSOR, DEFAULT_TAX_SENSOR),
            surcharge_sensor=conf.get(CONF_SURCHARGE_SENSOR, DEFAULT_SURCHARGE_SENSOR),
            employer_helper=conf.get(CONF_EMPLOYER_HELPER, DEFAULT_EMPLOYER_HELPER),
            employer_sensor=conf.get(CONF_EMPLOYER_SENSOR, DEFAULT_EMPLOYER_SENSOR),
            employer_rate=conf.get(CONF_EMPLOYER, DEFAULT_EMPLOYER_RATE),
            vat=conf.get(CONF_VAT, DEFAULT_VAT),
            declarant=Declarant.from_config(conf.get(CONF_DECLARATIE)),
        )
