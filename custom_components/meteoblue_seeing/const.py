"""Constants for the Meteoblue Seeing custom integration."""

DOMAIN = "meteoblue_seeing"
DEFAULT_NAME = "Meteoblue Seeing"
CONF_TIMEZONE = "timezone"
# Deliberately a polite refresh cadence; local clock ticks still advance
# sensors every hour without re-downloading the web page.
UPDATE_HOURS = 3
HOUR_TICK_SIGNAL = "meteoblue_seeing_hour_tick_{}"
