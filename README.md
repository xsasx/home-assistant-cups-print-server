# CUPS Print Server for Home Assistant

[![HACS Validation](https://github.com/xsasx/home-assistant-cups-print-server/actions/workflows/hacs.yml/badge.svg)](https://github.com/xsasx/home-assistant-cups-print-server/actions/workflows/hacs.yml)
[![hassfest](https://github.com/xsasx/home-assistant-cups-print-server/actions/workflows/hassfest.yml/badge.svg)](https://github.com/xsasx/home-assistant-cups-print-server/actions/workflows/hassfest.yml)
[![GitHub Release](https://img.shields.io/github/v/release/xsasx/home-assistant-cups-print-server?include_prereleases)](https://github.com/xsasx/home-assistant-cups-print-server/releases)
[![GitHub Issues](https://img.shields.io/github/issues/xsasx/home-assistant-cups-print-server)](https://github.com/xsasx/home-assistant-cups-print-server/issues)

A custom Home Assistant integration for monitoring **CUPS print servers, printer queues and print jobs via IPP**.

Everything runs locally. No cloud service, SSH access or shell commands from Home Assistant are required.

> **Status:** `v0.1.0-beta.1` – first public beta.

---

## ☕ Support the project

If this integration is useful to you and you'd like to support its development, you can buy me a coffee.

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/Xdog9YD)

Thank you for your support! ❤️

---

## 💡 Why this integration exists

This project started with a very practical problem.

My **Dell C2660dn** is still a perfectly usable network printer, but direct AirPrint printing of some PDF files resulted in a printer-side PDL emulation error.

The solution was to put a **CUPS print server** in front of the printer.

Once CUPS was running reliably, the next question was obvious:

**Why not monitor the print server and its jobs directly in Home Assistant?**

That idea became **CUPS Print Server for Home Assistant**.

The integration connects directly to CUPS using IPP and exposes printer, queue and print-job information as Home Assistant entities.

---

## ✨ Features

- UI setup through Home Assistant Config Flow
- Local polling over IPP/CUPS
- Automatic discovery of CUPS printer queues
- One Home Assistant device per CUPS printer queue
- Printer status
- Number of queued print jobs
- Current print job
- Current job ID
- Current job status
- Number of completed/printed pages
- Last print job
- Last print time
- Detailed print-job information as entity attributes
- Native Home Assistant timestamp handling
- Translated printer and job states
- German and English translations
- Diagnostics support
- Home Assistant device registry integration
- No SSH or shell access required
- No external Python dependency
- No cloud connection required

---

## 🖨️ Entities

For every discovered CUPS printer queue, the integration creates a Home Assistant device with the following sensors:

| Sensor | Description |
|---|---|
| Status | Current CUPS printer state |
| Queued jobs | Number of jobs currently waiting or processing |
| Current job | Name of the current print job |
| Current job ID | CUPS job ID |
| Current job status | Current state of the active print job |
| Pages completed | Number of pages completed for the current job |
| Last job | Most recent print job |
| Last print time | Timestamp of the most recent print job |

Depending on the information supplied by CUPS and the print client, additional job information is available as entity attributes.

This can include:

- Job ID
- Job state
- Job state reason
- Originating user
- Document name
- Document format
- Job size
- Number of copies
- Paper/media
- Page size
- Color mode
- Duplex mode
- Completed impressions/pages
- Creation time
- Processing time
- Completion time

Not every client supplies every attribute. For example, some AirPrint jobs may not provide a useful document name or username.

---

## 📦 Installation with HACS

### Custom repository

Until the integration is available through the default HACS repository list:

1. Open **HACS** in Home Assistant.
2. Open the menu in the upper-right corner.
3. Select **Custom repositories**.
4. Add:

   `https://github.com/xsasx/home-assistant-cups-print-server`

5. Select **Integration** as the repository type.
6. Install **CUPS Print Server**.
7. Restart Home Assistant.

Then go to:

**Settings → Devices & services → Add integration**

Search for:

**CUPS Print Server**

Enter the IP address or hostname of your CUPS server.

The default IPP port is:

`631`

Printer queues are discovered automatically.

---

## 🛠️ Manual installation

Copy:

`custom_components/cups_print_server`

to:

`/config/custom_components/cups_print_server`

Your directory should look like this:

~~~text
/config/
└── custom_components/
    └── cups_print_server/
        ├── __init__.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── diagnostics.py
        ├── ipp.py
        ├── manifest.json
        ├── sensor.py
        ├── brand/
        │   └── icon.png
        └── translations/
            ├── de.json
            └── en.json
~~~

Restart Home Assistant and add the integration through:

**Settings → Devices & services → Add integration → CUPS Print Server**

---

## ⚙️ Requirements

You need:

- A running CUPS server
- Network access from Home Assistant to the CUPS server
- IPP access to CUPS
- At least one configured CUPS printer queue

The standard CUPS/IPP port is TCP **631**.

The integration does **not** require SSH access to the CUPS server.

---

## 🔒 Local communication

CUPS Print Server communicates directly between Home Assistant and your CUPS server.

No external cloud service is required.

Your print-job information remains inside your local network unless your own Home Assistant or CUPS setup exposes it elsewhere.

---

## 🌍 Languages

Currently included:

- 🇬🇧 English
- 🇩🇪 German

Additional translations are welcome.

---

## 🚧 Beta notice

This is the first public beta.

The integration is already usable for monitoring CUPS printers and print jobs, but there may still be CUPS versions, printer drivers or print clients that expose IPP information differently.

If you find a problem, please open a GitHub issue and include:

- Home Assistant version
- CUPS version
- Printer model
- Relevant diagnostics
- Description of how the print job was submitted

Please remove any private information before posting diagnostics publicly.

---

## 🗺️ Planned features

Possible future additions include:

- Cancel active print jobs
- Pause printer queues
- Resume printer queues
- Improved print-job history
- Additional queue statistics
- More CUPS/IPP attributes
- Additional translations

Suggestions and pull requests are welcome.

---

## 🐛 Issues & feature requests

Found a bug or have an idea?

Please use the [GitHub issue tracker](https://github.com/xsasx/home-assistant-cups-print-server/issues).

---

## ❤️ Contributing

Bug reports, feature requests, translations and pull requests are welcome.

If you're testing the integration with another CUPS setup or printer model, feedback is especially useful during the beta phase.

---

## 📄 License

This project is licensed under the MIT License.
