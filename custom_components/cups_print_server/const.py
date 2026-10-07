"""Constants for the CUPS Print Server integration."""

DOMAIN = "cups_print_server"

CONF_PORT = "port"
CONF_USE_SSL = "use_ssl"

DEFAULT_PORT = 631
DEFAULT_USE_SSL = False
DEFAULT_SCAN_INTERVAL = 10

PLATFORMS = ["sensor"]

PRINTER_ATTRS = [
    "printer-name",
    "printer-info",
    "printer-location",
    "printer-state",
    "printer-state-message",
    "printer-state-reasons",
    "printer-make-and-model",
    "queued-job-count",
    "printer-is-accepting-jobs",
    "color-supported",
]

JOB_ATTRS = [
    "job-id",
    "job-uri",
    "job-name",
    "job-state",
    "job-state-reasons",
    "job-originating-user-name",
    "document-name-supplied",
    "document-format",
    "document-format-supplied",
    "job-impressions",
    "job-impressions-completed",
    "job-media-sheets",
    "job-media-sheets-completed",
    "job-k-octets",
    "copies",
    "media",
    "PageSize",
    "print-color-mode",
    "ColorModel",
    "sides",
    "date-time-at-creation",
    "date-time-at-processing",
    "date-time-at-completed",
]
