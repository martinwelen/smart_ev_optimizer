# Smart EV Optimizer

A HACS-compatible custom integration for [Home Assistant](https://www.home-assistant.io/) that optimizes multi-vehicle EV charging by balancing electricity prices, solar production, battery storage, grid power limits, and safety constraints.

**Key capabilities:**

- **Opportunity cost optimization** -- decides whether to charge now or export solar and charge later at cheaper night rates
- **Calendar hour power tracking (effekttaxa)** -- keeps average consumption within your power tariff limit per calendar hour, matching the Swedish grid billing model
- **Multi-vehicle priority** -- allocates available capacity across vehicles by configurable priority
- **Grid Rewards safety** -- automatically pauses charging during Grid Rewards events when the home battery is exporting
- **Easee charger master control** -- sends dynamic current limits to Easee chargers via circuit-level services

---

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant.
2. Go to **Integrations** and click the three-dot menu in the top right.
3. Select **Custom repositories** and add this repository URL with category **Integration**.
4. Search for **Smart EV Optimizer** and click **Install**.
5. Restart Home Assistant.

### Manual

1. Download or clone this repository.
2. Copy the `custom_components/smart_ev_optimizer` folder into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.

---

## Configuration

Add the integration via **Settings > Devices & Services > Add Integration > Smart EV Optimizer**. The config flow walks through four steps:

### Step 1 -- Site Sensors

| Field | Description |
|-------|-------------|
| Grid power sensor | Real-time grid import/export in Watts (e.g. from Tibber Pulse) |
| Solar power sensor | Current solar production in Watts |
| Battery power sensor | Home battery charge/discharge in Watts (negative = exporting) |
| Battery SoC sensor | Home battery state of charge in percent |
| Nordpool sensor | Spot price entity from the Nordpool integration |
| Grid Rewards entity | (Optional) Binary sensor or sensor indicating an active Grid Rewards event |

### Step 2 -- Economics

| Field | Description |
|-------|-------------|
| Grid fee import | Your grid operator's import fee in SEK/kWh |
| Grid fee export | Your grid operator's export fee in SEK/kWh |
| Export compensation | Any additional compensation you receive for export in SEK/kWh |
| VAT rate | Value-added tax rate (default 0.25 for Sweden) |

### Step 3 -- Power Limits

| Field | Description |
|-------|-------------|
| Power limit kW | Maximum average power per calendar hour in kW (your effekttaxa threshold) |

### Step 4 -- Vehicles

| Field | Description |
|-------|-------------|
| Name | Human-readable vehicle name |
| Priority | Charging priority (1 = highest, allocated first) |
| Charger entity | Easee charger sensor entity |
| SoC entity | (Optional) Vehicle state-of-charge sensor |
| Target SoC | Stop charging at this percentage (default 80%) |
| Departure entity | (Optional) Input datetime or sensor for next planned departure |

Additional vehicles can be added later via **Options** on the integration card.

---

## Prerequisites and Conflict Management

This section is critical for safe and correct operation. Read it carefully before enabling the integration.

### Disable External Smart Charging

Smart EV Optimizer requires **exclusive control** over your EV chargers. You **must** disable all built-in smart charging features in:

- **Tibber app** -- turn off smart charging / scheduled charging for EVs
- **Easee cloud** -- remove any cloud-based charging schedules
- **Vehicle manufacturer app** -- disable the car's own scheduled or smart charging features

Having multiple systems try to control the same charger simultaneously creates dangerous conflicts. The optimizer cannot guarantee main fuse safety or correct economic optimization if another system is also sending current limits or start/stop commands.

### Keep Data Streams Active

While you must disable external **charging control**, you should keep the following **data sources** running:

- **Tibber Pulse** -- real-time power measurement must remain active (the optimizer reads it, but does not use Tibber's charging features)
- **Homevolt / battery management** -- let your battery system continue its own charge/discharge management
- **Nordpool integration** -- spot price data must remain available
- **Easee HACS integration** -- required for charger communication (see below)

Only disable the EV charging **control** features of these services, not their data feeds.

### API Polling Conflicts

If multiple integrations poll the vehicle's cloud API for state-of-charge data, the car may never enter deep sleep. This gradually drains the 12V battery and can prevent the car from starting.

**Recommendation:** configure only one integration to poll the vehicle API. If you use Smart EV Optimizer's SoC entity from a car integration (e.g. Tesla, Polestar, Volvo), make sure no other integration is also polling the same vehicle.

### Hardware Requirements

This integration is designed to work with **Easee chargers** and requires the [Easee HACS integration](https://github.com/nordicopen/easee_hacs) (not the core Easee integration). The HACS version provides circuit-level dynamic limit services needed for proper load balancing across multiple chargers.

---

## Exposed Entities

After setup, the integration creates the following entities per installation. Per-vehicle entities are created for each configured vehicle.

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.seo_decision_reason` | Human-readable explanation of the current charging decision |
| `sensor.seo_calendar_hour_avg_kw` | Average power consumption for the current calendar hour (kW) |
| `sensor.seo_available_capacity_kw` | Remaining headroom to the power limit (kW) |
| `sensor.seo_opportunity_cost` | Net opportunity cost: export revenue minus night charging cost (SEK/kWh) |
| `sensor.seo_{vehicle}_allocated_amps` | Current allocated to this vehicle (A) |
| `sensor.seo_{vehicle}_allocated_phases` | Number of phases allocated to this vehicle |

### Binary Sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.seo_grid_rewards_active` | On when a Grid Rewards event is active |
| `binary_sensor.seo_obc_cooldown_active` | On during the on-board charger cooldown period after a phase switch |
| `binary_sensor.seo_{vehicle}_charging` | On when this vehicle is actively receiving current |

### Switches

| Entity | Description |
|--------|-------------|
| `switch.seo_force_charge_{vehicle}` | Force-charge this vehicle regardless of optimization logic |
| `switch.seo_pause_all_charging` | Emergency stop -- immediately pause all EV charging |

### Numbers

| Entity | Description |
|--------|-------------|
| `number.seo_power_limit_kw` | Adjust the site power ceiling at runtime (kW) |
| `number.seo_{vehicle}_target_soc` | Set per-vehicle target state of charge (%) |

### Select

| Entity | Description |
|--------|-------------|
| `select.seo_connected_vehicle` | Manually override which vehicle is assigned to the charger |

---

## Dashboard

See `dashboard_example.yaml` in this repository for a ready-made Lovelace dashboard card configuration that visualizes all the entities above.

---

## Troubleshooting

### Charging not starting

Check if your charger shows **"Awaiting Smart Charging"** in the Easee app. This means an external cloud schedule is overriding local control. Solution: disable Tibber smart charging and remove all Easee cloud schedules.

### Charger not responding to current limits

Verify that you have the **Easee HACS integration** installed (`nordicopen/easee_hacs`), not the core Home Assistant Easee integration. Also verify that the `circuit_id` and `charger_id` are correct in your configuration.

### Grid Rewards pausing unexpectedly

Check the sign convention of your battery power sensor. The safety module treats **negative values as export** (battery discharging to grid). If your sensor uses the opposite convention, Grid Rewards events will incorrectly trigger a charging pause.

### Power limit exceeded

Verify that the grid sensor entity is correct and actively updating. The sensor value must be in **Watts**. If the sensor reports in kilowatts, the calendar hour average will be off by a factor of 1000.

### Vehicle SoC not updating

Check that the SoC source entity exists and is reporting a numeric value. For vehicles that rely on a cloud API (Tesla, Polestar, etc.), verify that the corresponding car integration is authenticated and functioning.

---

## Decision Pipeline

Every update cycle (default: 30 seconds), the coordinator runs a four-step decision pipeline:

1. **Safety** -- checks Grid Rewards status, OBC cooldown timers, and grid meter availability. If unsafe conditions are detected, all charging is paused immediately.

2. **Constraints** -- records the current grid power sample and calculates the calendar-hour average. Determines how many kilowatts of headroom remain before hitting the effekttaxa power limit.

3. **User Intent** -- processes any force-charge switches. Force-charged vehicles receive power allocation first, before the optimizer runs.

4. **Optimization** -- evaluates the opportunity cost of charging now versus exporting solar and charging at cheaper night rates. If charging now is economically favorable (or if no night prices are available), remaining capacity is allocated to normal vehicles by priority.

If the grid meter becomes unavailable, the system enters **safe mode** and limits all charging to 6A to prevent exceeding the main fuse.

---

## Economics

The optimizer compares two strategies every cycle:

**Export revenue** (sell solar now):

```
export_revenue = spot_price + export_compensation - grid_fee_export
```

Export revenue is calculated without VAT and without tax reduction, as these depend on individual tax situations and are settled annually.

**Night charge cost** (charge the EV at the cheapest upcoming night rate):

```
night_charge_cost = (cheapest_night_spot + grid_fee_import) * (1 + VAT)
```

Night charging cost includes VAT because this is the actual price you pay.

**Decision rule:**

- If `export_revenue > night_charge_cost`: it is more profitable to export solar now and charge the EV at night. Charging is deferred.
- If `export_revenue <= night_charge_cost`: charging now is at least as cheap. The optimizer allocates power to connected vehicles.
- If no night prices are available (e.g. Nordpool data not yet published), charging proceeds immediately.

---

## License

MIT License

Copyright (c) 2026 Martin Welen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
