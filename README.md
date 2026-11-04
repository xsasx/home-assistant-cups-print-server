# CUPS Print Server for Home Assistant

[![HACS Validation](https://github.com/xsasx/home-assistant-cups-print-server/actions/workflows/hacs.yml/badge.svg)](https://github.com/xsasx/home-assistant-cups-print-server/actions/workflows/hacs.yml)
[![hassfest](https://github.com/xsasx/home-assistant-cups-print-server/actions/workflows/hassfest.yml/badge.svg)](https://github.com/xsasx/home-assistant-cups-print-server/actions/workflows/hassfest.yml)
[![GitHub Release](https://img.shields.io/github/v/release/xsasx/home-assistant-cups-print-server?include_prereleases)](https://github.com/xsasx/home-assistant-cups-print-server/releases)
[![GitHub Issues](https://img.shields.io/github/issues/xsasx/home-assistant-cups-print-server)](https://github.com/xsasx/home-assistant-cups-print-server/issues)

A custom Home Assistant integration for monitoring **CUPS print servers, printer queues and print jobs via IPP**, with optional **smart plug power management**.

Everything runs locally. No cloud service, SSH access or shell commands from Home Assistant are required.

> **Status:** `0.1.0` stable release prepared; publication on GitHub Releases is pending.

---

## ☕ Support the project

If this integration is useful to you and you'd like to support its development, you can buy me a coffee.

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/xsas1337)

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

Starting with `v0.1.0-beta.7`, the integration also supports an optional Home Assistant smart plug to automatically power a printer on when a print job arrives and switch it off again after a configurable idle period.

---

## ✨ Features

### 🖨️ Printer and print-job monitoring

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

### 🔌 Smart plug power management

- Select an existing Home Assistant smart plug
- Manually turn printer power on and off
- Automatically power on the printer when an active CUPS job is detected
- Automatically power off the printer after a configurable idle period
- Adjustable shutdown delay from 1 to 1440 minutes
- Default shutdown delay of 15 minutes
- Countdown sensor showing the remaining shutdown time
- Separate switches for automatic power-on and power-off
- Additional CUPS job-state verification before automatic shutdown
- Power management controls directly on the printer's Home Assistant device
- Power automation can be disabled independently

### 🔒 Local operation

- No SSH or shell access required
- No external Python dependency
- No cloud connection required
- Uses Home Assistant's existing switch entities for power control

---

## 🖨️ Entities

For every discovered CUPS printer queue, the integration creates a Home Assistant device.

### Printer monitoring

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

### Smart plug power management — NEW

When a smart plug is configured, the printer device includes additional controls.

| Entity | Type | Description |
|---|---|---|
| Printer power | Switch | Manually control the configured smart plug |
| Automatic power on | Switch | Enable or disable power-on when a print job is detected |
| Automatic power off | Switch | Enable or disable idle shutdown |
| Power-off delay | Number | Configure the idle delay in minutes |
| Remaining shutdown time | Sensor | Countdown until automatic power-off, in seconds |

The countdown is unavailable when no shutdown timer is active.

The controls use the configured Home Assistant smart plug and do not require the printer to provide native power-management capabilities.

**Current limitation:** The smart plug configuration and automation settings are shared across printer queues belonging to the same CUPS integration entry. Independent per-printer smart plugs are not yet supported within one entry.

---

## 🔌 Smart plug power management

Starting with `v0.1.0-beta.7`, CUPS Print Server can automatically control a printer's power supply using a smart plug already integrated into Home Assistant.

This is especially useful for printers that consume unnecessary power while idle.

### Requirements

- A working CUPS Print Server integration
- A smart plug exposed as a `switch` entity in Home Assistant
- A printer connected through that smart plug
- CUPS must retain pending print jobs long enough for the printer to become available

The smart plug can use any supported Home Assistant integration that provides a compatible switch entity.

### Configuration

1. Open **Settings → Devices & services**.
2. Select **CUPS Print Server**.
3. Open **Configure**.
4. Select the smart plug connected to the printer.
5. Enable **Automatic power on**, if desired.
6. Enable **Automatic power off**, if desired.
7. Configure the shutdown delay.

The default delay is **15 minutes**.

The power-management entities appear on the existing printer device.

### Automatic power-on

When a CUPS print job is detected:

1. The integration checks the active print jobs.
2. If automatic power-on is enabled and the smart plug is off, Home Assistant switches it on.
3. The printer begins its startup process.
4. CUPS continues processing the queued job according to its own retry and printer-availability behavior.

**Important:** The integration switches on the power supply, but does not control the printer's boot process or guarantee that CUPS will automatically retry every failed job. This depends on the printer and CUPS configuration.

### Automatic power-off

When automatic power-off is enabled:

1. The integration monitors the CUPS queues.
2. If no active jobs are detected and the smart plug is on, the idle timer begins.
3. The remaining time is exposed through the countdown sensor.
4. New active jobs reset the idle timer.
5. When the delay expires, the integration queries CUPS again.
6. If no active jobs are found and queue data is available, the smart plug is switched off.

If CUPS cannot provide reliable current queue data, automatic shutdown is skipped.

This additional verification reduces the risk of interrupting a print job. However, polling-based control cannot eliminate every race condition, such as a new job arriving immediately after the final check.

### Manual control

The printer's power switch can also be operated manually through Home Assistant.

Manual power control works independently of the automatic power-on and power-off settings.

If automatic power-on is enabled and a job remains active, the integration may switch the printer back on after it has been manually switched off.

### Recommended settings

For a typical home printer:

| Setting | Recommended value |
|---|---|
| Automatic power on | Enabled |
| Automatic power off | Enabled |
| Power-off delay | 15 minutes |

For initial testing, keep automatic power-off disabled until the printer's startup and CUPS job-processing behavior have been verified.

### Important limitations

- A smart plug must be configured before power control is available.
- The integration uses periodic polling, not instant event-based detection.
- The printer must support being powered on safely through its external power supply.
- Some printers require manual confirmation after power restoration.
- CUPS may need retry configuration if the printer is initially unreachable.
- Automatic shutdown should not be enabled for printers that must remain continuously powered.
- Avoid conflicting Home Assistant automations that independently control the same smart plug.

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

### Updating from an earlier version

1. Open HACS.
2. Select CUPS Print Server.
3. Install the latest published release.
4. Restart Home Assistant.
5. Open the integration configuration to select your smart plug and configure the power-management options.

Existing printer monitoring entities should remain available.

---

## 🛠️ Manual installation

Copy:

`custom_components/cups_print_server`

to:

`/config/custom_components/cups_print_server`

Your directory should look similar to this:

```text
/config/
└── custom_components/
    └── cups_print_server/
        ├── __init__.py
        ├── binary_sensor.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── diagnostics.py
        ├── ipp.py
        ├── manifest.json
        ├── number.py
        ├── power.py
        ├── power_sensor.py
        ├── sensor.py
        ├── switch.py
        ├── strings.json
        ├── brand/
        │   └── icon.png
        └── translations/
            ├── de.json
            └── en.json
```

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

Smart plug power management additionally requires a suitable Home Assistant switch entity.

---

## 🔒 Local communication

CUPS Print Server communicates directly between Home Assistant and your CUPS server.

No external cloud service is required by the integration itself.

Smart plug control uses Home Assistant's switch service. Whether the smart plug requires cloud connectivity depends on the smart plug integration being used.

Your print-job information remains inside your local network unless your own Home Assistant or CUPS setup exposes it elsewhere.

---

## 🌍 Languages

Currently included:

- 🇬🇧 English
- 🇩🇪 German

Additional translations are welcome.

---

## 🧪 Testing and compatibility

The integration supports printer and job monitoring as well as optional smart plug power management.

Automated regression tests cover IPP parsing and smart plug safety decisions. HACS validation and hassfest are also run through GitHub Actions.

The Dell C2660dn test setup has been used to verify automatic power-on, successful print-job completion, and idle shutdown.

Other CUPS versions, printer drivers, print clients, and smart plug configurations may behave differently. Please report compatibility issues through the issue tracker.

If you find a problem, please open a GitHub issue and include:

- Home Assistant version
- CUPS version
- Printer model
- Smart plug integration, if applicable
- Relevant diagnostics
- Description of how the print job was submitted
- Whether automatic power-on or power-off was enabled

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
- Independent smart plug configuration for multiple printers
- Improved handling of printer startup and CUPS retry behavior
- Additional translations

Suggestions and pull requests are welcome.

---

## 🐛 Issues & feature requests

Found a bug or have an idea?

Please use the [GitHub issue tracker](https://github.com/xsasx/home-assistant-cups-print-server/issues).

---

## ❤️ Contributing

Bug reports, feature requests, translations and pull requests are welcome.

If you're testing the integration with another CUPS setup, printer model or smart plug, feedback is especially useful for expanding compatibility.

---

## 📄 License

This project is licensed under the MIT License.
