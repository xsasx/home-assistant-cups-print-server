# CUPS Print Server for Home Assistant

A custom Home Assistant integration for monitoring CUPS print servers, printer queues and print jobs over IPP.

> **Status:** v0.1.0-beta.1 – first public beta.

## Features

- UI setup through Home Assistant Config Flow
- Local polling over IPP/CUPS
- Automatic discovery of CUPS printer queues
- One Home Assistant device per CUPS queue
- Printer state
- Number of queued jobs
- Current print job and job ID
- Current job state
- Completed pages
- Last print job
- Last print time
- Detailed job information as entity attributes
- German and English translations
- Diagnostics support
- No SSH or shell access required
- No external Python dependency

## Installation with HACS

1. Open HACS in Home Assistant.
2. Add this repository as a custom repository of type **Integration**.
3. Install **CUPS Print Server**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration**.
6. Search for **CUPS Print Server**.
7. Enter the IP address or hostname of your CUPS server. The default port is `631`.

## Manual installation

Copy:

`custom_components/cups_print_server`

to:

`/config/custom_components/cups_print_server`

and restart Home Assistant.

## Tested setup

The first beta was developed and tested against CUPS using IPP on port 631 with a network printer queue. The integration is designed to be printer-independent; it reads data from CUPS rather than communicating directly with the physical printer.

## Beta notice

This is an early beta. Please report issues and include Home Assistant diagnostics where useful.

## Planned

- Cancel print job
- Pause/resume printer queue
- Improved job history
- Additional job/page statistics
- More configuration options

## Issues

Please use the GitHub issue tracker:
https://github.com/xsasx/home-assistant-cups-print-server/issues

## License

MIT
