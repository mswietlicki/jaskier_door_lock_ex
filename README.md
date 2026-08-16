# 12 V Linear-Actuator Door Lock

ESPHome door lock for Home Assistant: an ESP32 drives a **DRV8871** H-bridge into a
12 V linear actuator, with an **INA219** high-side shunt reading motor current.
End of travel *and* obstructions are both detected from that current — no extra sensors.
Powered from a 4S LiFePO₄ pack via an **MH-MINI-360** buck.

Two variants share the same per-door state machine:

| Variant | Config | ESP | Doors |
|---|---|---|---|
| **A** | `door_lock_a.yaml` | ESP32-C3-Zero (Waveshare) | 1 |
| **B** | `door_lock_b.yaml` | ESP32-S3-DevKitC-1 | 4, fully independent, one board |

Everything below describes variant A; [Variant B](#variant-b--four-doors-one-board)
documents only what differs (pins, addresses, BOM, power).

| | |
|---|---|
| Pack | 4S LiFePO₄ · 12.8 V nominal · 10.0 – 14.6 V |
| Measured stall current | ≈ 0.50 A |
| Default thresholds | 0.40 A stall / 0.60 A hard limit / 0.01 A idle |
| Shunt | 0.1 Ω · 0.8 mA resolution |
| I²C | GPIO8 (SDA) / GPIO9 (SCL) · address 0x40 |
| Bridge | GPIO6 (IN1) / GPIO7 (IN2) · full on/off, **no PWM** |

## Repository layout

```
door_lock_a.yaml             variant A - single door on an ESP32-C3-Zero
door_lock_b.yaml             variant B - four doors on an ESP32-S3-DevKitC-1
packages/door.yaml           one door's state machine, included 4x by variant B
secrets.yaml.example         copy to secrets.yaml and fill in
docs/wiring.html             full illustrated build document for variant A
docs/wiring_b.html           full illustrated build document for variant B
docs/diagrams/
  fig1-wiring.svg            complete wiring diagram, all pinouts (variant A)
  fig2-position-switches.svg optional position feedback
  fig3-move-outcomes.svg     how a move terminates
  figB1-wiring.svg           complete wiring diagram, four doors (variant B)
```

---

## Read this first

> [!CAUTION]
> **Set the buck converter output before connecting anything to it.**
> The MH-MINI-360 ships with its trimpot in an arbitrary position and will happily pass
> close to 12 V straight through. The ESP32-C3-Zero's `5V` pad accepts **3.7 – 6 V**;
> above that you destroy the regulator and probably the chip.
> Wire U4 to the pack *with nothing on its output*, measure OUT+ to OUT−, trim to
> **5.00 V**, power down, then connect U1.

> [!WARNING]
> **Two things a door lock has to get right.** Keep a mechanical override — a key
> cylinder or thumb turn — that works with the electronics dead. And make sure the
> actuator cannot trap anyone inside: the bolt must be releasable from the protected
> side without power.

The firmware drives the bridge **fully on, never PWM**. PWM would chop the current the
INA219 sees and make stall detection unreliable, so the actuator only ever runs at full
speed. Adding soft-start later means an RC filter on the sense path and higher thresholds.

---

## Wiring

![Complete wiring diagram](docs/diagrams/fig1-wiring.svg)

**The current path is the whole design.** Pack → F1 → +12 V rail → U3's 0.1 Ω shunt →
U2 Power + → motor. Because the shunt sits upstream of the bridge, one INA219 gives you
both motor current *and* pack voltage, and its bus-voltage input never sees the chopped
motor node. U3's own GND runs back to the star point as a separate wire so motor return
current does not corrupt the measurement.

U2's `VM` and `GND` header pins are the same nets as the `Power ±` screw terminal —
populate one or the other, not both.

### Net list

Build in this order. Everything in the 12 V group carries motor current: keep it short,
thick, and away from the I²C pair.

| Net | From | To | Wire | Notes |
|---|---|---|---|---|
| `+12V_BAT` | BAT1 + | F1 | 18 AWG | Screw terminal at the board edge |
| `+12V_BAT` | F1 | D1 anode | 18 AWG | D1 optional; omit and polarity is on you |
| `+12V` | D1 cathode | +12 V rail | 18 AWG | Rail = a length of bare 18 AWG along the board |
| `+12V` | +12 V rail | U4 IN+ | 22 AWG | Logic supply branch |
| `+12V` | +12 V rail | U3 VIN+ | 20 AWG | Motor branch enters the shunt here |
| `VM` | U3 VIN− | U2 Power + | 20 AWG | Shunt output — the only path to the bridge |
| `M+` | U2 Motor + | M1 lead A | 20 AWG | Twist the pair; swap A/B if travel is inverted |
| `M−` | U2 Motor − | M1 lead B | 20 AWG | C3 100 nF across the two, at the motor end |
| `+5V` | U4 OUT+ | U1 5V | 24 AWG | **Verify 5.00 V before connecting** |
| `+3V3` | U1 3V3 | U3 VCC | 26 AWG | Also supplies the module's I²C pull-ups |
| `SDA` | U1 GPIO8 | U3 SDA | 26 AWG | Keep under 15 cm, away from motor leads |
| `SCL` | U1 GPIO9 | U3 SCL | 26 AWG | Same pin as the BOOT button — see pinout note |
| `IN1` | U1 GPIO6 | U2 IN1 | 26 AWG | High = drive towards UNLOCKED |
| `IN2` | U1 GPIO7 | U2 IN2 | 26 AWG | High = drive towards LOCKED |
| `IN1` | U2 IN1 | R1 10 k → GND | — | Fit at U2's header, not at U1 |
| `IN2` | U2 IN2 | R2 10 k → GND | — | Holds the bridge off while U1 resets |
| `C1` | U2 Power + | U2 Power − | — | 100 µF / 25 V electrolytic, under 20 mm of lead |
| `C2` | U2 Power + | U2 Power − | — | 100 nF ceramic, right next to C1 |
| `GND` | BAT1 − | GND rail | 18 AWG | This point is the star — nothing daisy-chains past it |
| `GND` | U2 Power − | GND rail | 20 AWG | Motor return; own wire straight to the star |
| `GND` | U4 IN− and OUT− | GND rail | 22 AWG | Both pads, joined at the board |
| `GND` | U1 GND | GND rail | 24 AWG | Own wire — do not share with the motor return |
| `GND` | U3 GND | GND rail | 24 AWG | Own wire — this is the measurement reference |

### Perfboard layout

The schematic is drawn as three horizontal rails because that is how it should be built:
a bare 18 AWG +12 V rail along the top, a bare 18 AWG GND rail along the bottom, logic
between them.

- **C1 and C2 go at U2's power terminals**, not near the battery. Perfboard wire has real
  inductance, and a 12 V motor switching on at the far end of 30 cm of it will brown out
  the bridge without them.
- **Keep the motor loop tight.** U3 → U2 → motor terminals should be the shortest run on
  the board. Twist the two motor leads together for their whole length.
- **Star the grounds.** Four separate returns land at BAT1 −: U2's motor return, U4's,
  U1's, U3's. Do not let U1 or U3 ground *through* U2's return path — that is the single
  most common cause of nonsense current readings.
- **Put the I²C pair on the opposite side of U1** from the motor wiring, under ~15 cm.
  The 10 k pull-ups on the INA219 module are weak; if the bus scan is flaky, add 4.7 k
  from SDA and SCL to 3V3.
- **Screw terminals for anything leaving the board** — pack, motor. Soldered flying leads
  on perfboard fail at the joint under vibration, and a door slams a lot.
- **Fuse before everything.** F1 is the only thing between a 4S LiFePO₄ pack and a shorted
  perfboard trace; that pack will deliver tens of amps into a fault without noticing.

---

## Pinouts

### U1 — ESP32-C3-Zero (Waveshare)

18 castellated pads at 2.54 mm: three power, fifteen GPIO. GPIO11–GPIO17 are consumed by
the stacked 4 MB flash and are not brought out.

> Pin positions assume the board mounted with **USB-C uppermost** and the power pads on
> the left edge. Verify against the silkscreen before soldering.

| Edge | Pad | Wired to | Constraints worth knowing |
|---|---|---|---|
| L1 | `5V` | U4 OUT+ | Accepts 3.7 – 6 V. Feeds the on-board regulator. |
| L2 | `GND` | GND rail | — |
| L3 | `3V3` | U3 VCC | Regulator output. Budget ~200 mA for peripherals. |
| L4 | `GPIO0` | SW1 (optional) | ADC1_CH0. Also the 32 kHz XTAL pin — fine as digital I/O. |
| L5 | `GPIO1` | SW2 (optional) | ADC1_CH1. |
| L6 | `GPIO2` | *free* | **Strapping pin** — must be high or floating at boot. Do not pull it down. |
| L7 | `GPIO3` | *free* | ADC1_CH3. |
| L8 | `GPIO4` | *free* | ADC1_CH4. |
| L9 | `GPIO5` | SW3 button (optional) | ADC2 — unusable as an ADC while Wi-Fi is on. Digital is fine. |
| R1 | `GPIO6` | U2 IN1 | Plain GPIO, no strapping role. Good choice for the bridge. |
| R2 | `GPIO7` | U2 IN2 | Plain GPIO. |
| R3 | `GPIO8` | U3 SDA | Strapping pin that must be *high* at boot — the I²C pull-up satisfies that. |
| R4 | `GPIO9` | U3 SCL | BOOT button. Held low at reset it enters the ROM bootloader; I²C idles high so it never does. Don't press BOOT while the bus is live. |
| R5 | `GPIO10` | on-board WS2812 | Health and action indicator, RGB data order; no external wiring. |
| R6 | `GPIO18` | *reserved* | USB D−. Leave open or you lose USB flashing and logging. |
| R7 | `GPIO19` | *reserved* | USB D+. |
| R8 | `GPIO20` | *free* | UART0 RX. Free here because logging goes over USB. |
| R9 | `GPIO21` | *free* | UART0 TX. |

### ESP32-C3-Zero on-board LED

The firmware uses the GPIO10 WS2812 as a self-contained health and action indicator:

| LED | Meaning |
|---|---|
| Amber slow pulse | Firmware is alive and joining Wi-Fi. |
| Blue slow pulse | Wi-Fi is connected; waiting for the Home Assistant API. |
| Dim green | Home Assistant is connected and the lock reports locked. |
| Dim blue | Home Assistant is connected and the lock reports unlocked. |
| Dim amber | Home Assistant is connected and the position is unknown or stopped. |
| Magenta fast pulse | Locking. |
| Cyan fast pulse | Unlocking. |
| Green flash | Movement completed successfully. |
| Red fast pulse | Latched jam, timeout, current-sensor, or watchdog fault. |

The LED is driven by the application firmware, so a dark LED does not by itself prove that the board has no power. For USB recovery, hold **BOOT**, tap **RESET**, release **BOOT**, and flash the firmware while the board is in ROM download mode. See the [Waveshare ESP32-C3-Zero documentation](https://docs.waveshare.com/ESP32-C3-Zero).

### U2 — DRV8871 breakout (Adafruit 3190)

| Terminal | Type | Wired to | Notes |
|---|---|---|---|
| `Power +` | screw | U3 VIN− | 6.5 – 45 V. Same net as the header's `VM` pin. |
| `Power −` | screw | GND rail | Same net as the header's `GND` pin. |
| `Motor +` | screw | M1 lead A | OUT1 |
| `Motor −` | screw | M1 lead B | OUT2 |
| `VM` | header | *unused* | Duplicate of `Power +`. Use one or the other. |
| `IN1` | header | U1 GPIO6 | 1.5 V logic threshold — 3.3 V drive is fine. 10 k to GND. |
| `IN2` | header | U1 GPIO7 | 10 k to GND. |
| `GND` | header | *unused* | Duplicate of `Power −`. |
| R<sub>ILIM</sub> | on-board SMD | — | Sets the chip's own trip level to roughly 2 A. Leave it: F1 plus the firmware limit do the real work at 0.5 A. |

Input truth table: `00` coast (and low-power sleep) · `10` unlock · `01` lock · `11` brake.
The firmware never uses brake.

### U3 — INA219 module, 0.1 Ω shunt

| Pin | Wired to | Notes |
|---|---|---|
| `VCC` | U1 3V3 | 3.0 – 5.5 V. At 3.3 V the module's pull-ups match the ESP32's logic — no level shifter. |
| `GND` | GND rail (own wire) | Measurement reference. Route to the star point, not through the motor return. |
| `SCL` | U1 GPIO9 | 10 k pull-up on the module. |
| `SDA` | U1 GPIO8 | 10 k pull-up on the module. |
| `VIN+` | +12 V rail | High side of the shunt. Common mode up to 26 V — 12.8 V is comfortable. **Use the big pad, not the header pin.** |
| `VIN−` | U2 Power + | Low side of the shunt, and the bus-voltage sense node. **Big pad.** |
| `VIN+` / `VIN−` *(header)* | *leave empty* | Duplicates of the pads above — same copper, one 0.1 Ω shunt between them. Populate one pair only. |
| `A0` / `A1` | *open* | Both open = address 0x40. |

> [!WARNING]
> **Never bridge the shunt.** U3 brings `VIN+` and `VIN−` out twice: as large pads for
> load current, and again on the 6-way header. Each pair is the same copper. Wire the
> **big pair only** and leave the header pins empty.
>
> Land two wires from the same side of the circuit on both footprints and you short across
> the shunt. The motor still runs normally, so nothing looks broken — but current reads
> ≈ 0 A forever, every move ends instantly as "current collapsed", and jam detection never
> fires. Before wiring, check with a meter: `VIN+` to `VIN−` should read about **0.1 Ω**,
> and big-to-small on the same name about **0 Ω**.

### U4 — MH-MINI-360 (MP1584EN)

| Pad | Wired to | Notes |
|---|---|---|
| `IN+` | +12 V rail | 4.75 – 23 V. A 4S LiFePO₄ pack at 14.6 V is well inside range. |
| `IN−` | GND rail | — |
| `OUT+` | U1 5V | **Set to 5.00 V with the trimpot before connecting U1.** |
| `OUT−` | GND rail | — |
| trimpot | — | Multi-turn; clockwise usually raises output. Measure, don't guess. |

---

## Optional position feedback

![Optional position switch wiring](docs/diagrams/fig2-position-switches.svg)

The firmware works without these — lock state survives a reboot in flash. But
flash-restored state is a *belief*, not a measurement: if someone moves the bolt by hand
while the board is off, it will be wrong. Two reed or micro switches turn that belief into
a fact.

Internal pull-ups are enabled in firmware, so a closed switch pulls the pin to GND and
reads as active. Leaving these pads empty is harmless — the pins float high and read
inactive. For leads longer than about 30 cm add a 100 nF cap from each pin to GND at the
ESP32 end.

**Fit them, then enable them.** Turn on the *Use position switches* entity only once SW1
and SW2 are actually installed. With it on, a closed switch ends the move immediately and
overrides the current-based verdict.

---

## How a move ends

![The four ways a move terminates](docs/diagrams/fig3-move-outcomes.svg)

Every move is a race between four outcomes. The firmware samples the INA219 at 20 Hz,
ignores the first 400 ms of inrush, then needs **three consecutive samples** past a
threshold before it commits — one noisy reading never triggers anything.

1. **Current collapses below `idle current`** → the actuator's internal limit switch cut
   the motor at end of stroke → `LOCKED` / `UNLOCKED`.
2. **Current rises past `stall current` after `min travel time`** → the bolt reached its
   mechanical stop → `LOCKED` / `UNLOCKED`. (This is the path for actuators without
   internal limit switches.)
3. **Current rises past `stall current` before `min travel time`** → obstruction. Coast,
   wait, drive back out for as long as it drove in (capped at 4 s) → `JAMMED` + alert.
4. **Neither threshold reached by `max travel time`** → slipping clutch, broken linkage,
   bad wiring → `JAMMED` + alert.

A fifth path isn't drawn: after inrush blanking, current above `hard current limit`
aborts on the very first sample, with no debounce. Three consecutive invalid INA219
samples abort without back-off and latch a current-sensor fault; an invalid reading is
never treated as an open actuator limit switch.

**The only thing separating ② from ③ is the clock.** A stall after `min travel time` is
the bolt arriving; the same stall before it is an obstruction. That is why `min travel
time` must be set from a measured stroke rather than guessed.

---

## Bill of materials

| Ref | Part | Spec | Notes |
|---|---|---|---|
| U1 | Waveshare ESP32-C3-Zero | ESP32-C3FH4, 4 MB | Header version (`-M`) saves soldering castellations |
| U2 | Adafruit DRV8871 breakout | 6.5 – 45 V, 2 A / 3.6 A pk | — |
| U3 | INA219 module | 0.1 Ω, 0x40, ±3.2 A | Keep the 0.1 Ω shunt — at 0.5 A you want the resolution |
| U4 | MH-MINI-360 | MP1584EN, 1.8 A | Buy two; the trimpots are fragile |
| M1 | 12 V linear actuator | stall ≈ 0.5 A measured | Note whether it has internal limit switches |
| BAT1 | LiFePO₄ 4S pack | 12.8 V nom, BMS | 10.0 – 14.6 V across the whole cycle |
| F1 | Fuse + holder | 2 A slow-blow | Or a 1.5 A polyfuse if you prefer self-resetting |
| D1 | Schottky diode | SS54 / 1N5822 | Optional reverse-polarity protection, ~0.4 V drop |
| C1 | Electrolytic | 100 µF / 25 V | 35 V if the pack ever sees a charger |
| C2, C3 | Ceramic | 100 nF / 50 V | C2 at U2, C3 across the motor |
| R1, R2 | Resistor | 10 kΩ ¼ W | IN1 / IN2 pull-downs |
| SW1, SW2 | Reed or micro switch | NO, dry contact | Optional position feedback |
| SW3 | Momentary push-button | NO | Optional local override |

---

## Flashing

```bash
cp secrets.yaml.example secrets.yaml
```

Fill in `secrets.yaml`, generating the API key with:

```bash
openssl rand -base64 32
```

Then, with U1 on USB-C (use `door_lock_b.yaml` for variant B):

```bash
esphome run door_lock_a.yaml
```

Subsequent updates go over the air. Logs are available with:

```bash
esphome logs door_lock_a.yaml
```

## Commissioning

In this order. Steps 1–4 happen with the motor disconnected.

1. **Set the buck.** U4 on the pack, nothing on its output, meter on OUT+/OUT−, trim to
   5.00 V. Power down.
2. **Bring up U1 alone.** Flash over USB-C, then power it from U4 and confirm it joins
   Wi-Fi and Home Assistant.
3. **Confirm I²C.** The log should print `Found i2c device at address 0x40` at boot. If it
   doesn't, add 4.7 k pull-ups before doing anything else.
4. **Check the sense path.** With the motor unplugged but the 12 V branch live, *supply
   voltage* should read the pack voltage and *motor current* a few milliamps. If current
   reads a dead flat 0.000 A, suspect a bridged shunt before anything else — measure 0.1 Ω
   across U3's `VIN+`/`VIN−` with the power off.
5. **Verify direction.** Connect the motor. Press *Jog unlock* — a fixed 400 ms nudge with
   no protection logic. If the bolt goes the wrong way, swap the two motor leads at U2.
6. **Measure the real currents.** Watch *motor current* while jogging repeatedly and note
   the free-running value. Then hold the bolt and jog again to confirm the ~0.5 A stall.
7. **Set the thresholds** from what you measured (table below).
8. **Measure the stroke.** One full move; read *last move duration*. Set `min travel time`
   to about 70 % of it and `max travel time` to about 150 %.
9. **Test the jam path.** Block the bolt with something soft mid-travel and command a move.
   It must stop, reverse out, report *Jammed*, and set the fault sensor.

### Setting the thresholds

All six are Home Assistant `number` entities stored in flash — no reflashing to tune. What
matters is that the free-running current sits clearly between `idle current` and
`stall current`.

| Entity | Default | How to pick it |
|---|---|---|
| Idle current | 0.01 A | Well below the commissioned 0.04–0.06 A free-running current, above the ≈0.003 A standing reading. Three samples under this = limit switch opened. |
| Stall current | 0.40 A | Roughly midway between free-running and the 0.5 A stall. Raise it if normal moves trip a false jam. |
| Hard current limit | 0.60 A | Just above stall. After inrush blanking it trips on a single sample, with no debounce. |
| Inrush blanking | 400 ms | Long enough to cover the startup spike. Shorten only if the logs show the spike is over sooner. |
| Min travel time | 1500 ms | ≈ 70 % of the measured full stroke. Below this, a stall means an obstruction. |
| Max travel time | 4500 ms | Commissioned 1.7–2.8 s stroke plus cold-weather margin. Reaching it is a timeout fault. |

> [!IMPORTANT]
> **If free-running current is close to stall current.** A 0.5 A stall is low, which means
> the gap between running and stalled may be narrow — and that gap is what the whole
> detection scheme rests on. If you measure, say, 0.35 A running against 0.50 A stalled,
> current alone is too coarse: fit SW1/SW2 and let the switches call end-of-travel, leaving
> current detection purely as the jam guard.

---

## Home Assistant entities

| Entity | Type | What it's for |
|---|---|---|
| Door lock | `lock` | Lock / unlock. Reports Locking, Unlocking, Locked, Unlocked, or **Jammed**. |
| Motor current | `sensor` | 1 Hz. The state machine runs off a faster internal copy at 20 Hz. |
| Supply voltage | `sensor` | Pack voltage from the same INA219 — free LiFePO₄ monitoring. |
| Last move peak current | `sensor` | Diagnostic. Trend it and you'll see the mechanism stiffening before it fails. |
| Last move duration | `sensor` | Diagnostic. Also how you set the travel-time thresholds. |
| Fault | `binary_sensor` | Problem class. Latches until cleared. |
| Last result | `text_sensor` | Plain text: `locked`, `obstruction - stalled mid-travel`, and so on. |
| Stop | `button` | Aborts a move immediately, state goes unknown. |
| Clear fault | `button` | Drops the fault flag; the LED returns to the current connectivity and lock state. |
| Jog unlock / Jog lock | `button` | 400 ms bench nudge, no protection logic. Disabled by default; enable only while commissioning. |
| Use position switches | `switch` | Off by default. Turn on once SW1/SW2 exist. |
| Six thresholds | `number` | Config category. Stored in flash. |

### Alerting on a failed move

Two independent hooks — pick whichever fits. The lock entity going to `jammed`:

```yaml
automation:
  - alias: Door lock jammed
    trigger:
      - platform: state
        entity_id: lock.door_lock
        to: "jammed"
    action:
      - service: notify.mobile_app_phone
        data:
          title: Door lock failed
          message: >-
            {{ states('sensor.door_lock_last_result') }} —
            peak {{ states('sensor.door_lock_last_move_peak_current') }} A
```

…or the event the firmware fires, which carries the detail as attributes:

```yaml
automation:
  - alias: Door lock fault event
    trigger:
      - platform: event
        event_type: esphome.door_lock_fault
    action:
      - service: notify.mobile_app_phone
        data:
          title: "Door lock: {{ trigger.event.data.reason }}"
          message: >-
            While {{ trigger.event.data.direction }} —
            {{ trigger.event.data.peak_current }} A after
            {{ trigger.event.data.travel_ms }} ms
```

---

## Variant B — four doors, one board

`door_lock_b.yaml` runs **four fully independent doors** from one ESP and one perfboard.
Each door is a verbatim copy of the variant A state machine (factored out into
`packages/door.yaml` and included four times), so everything above — move outcomes,
thresholds, jam handling, commissioning — applies per door. Doors never wait on each
other; any or all four can move at once. A "close all" in Home Assistant is simply a
script/automation that calls `lock.lock` on all four entities.

The full illustrated build document for this variant — wiring diagram, net list,
complete DevKitC-1 pinout, BOM, commissioning — is **[docs/wiring_b.html](docs/wiring_b.html)**
(open in a browser).

![Variant B complete wiring diagram](docs/diagrams/figB1-wiring.svg)

### What changes against variant A

| | Variant A | Variant B |
|---|---|---|
| ESP | ESP32-C3-Zero | **ESP32-S3-DevKitC-1** — the C3 has ~11 usable GPIOs, four doors need ~23 |
| H-bridge | 1 × DRV8871 | 4 × DRV8871, one per door |
| Current sense | 1 × INA219 @ 0x40 | 4 × INA219 on the **same I²C bus** @ 0x40 / 0x41 / 0x44 / 0x45 |
| Pull-downs | R1, R2 | 10 k on **all eight** IN pins (R1–R8) |
| Fuse F1 | 2 A slow-blow | **5 A slow-blow** — four actuators stalling together draw ~2 A plus inrush |
| Supply voltage entity | from the INA219 | from door 1's INA219 only (all four sit on the same rail) |
| Status LED | per-move | aggregate: red = any fault · white = any door moving · green flash = a move finished |

Each door keeps its own 12 V branch: rail → its INA219 shunt → its DRV8871 → its motor,
exactly as in Figure 1, replicated four times off the shared +12 V and GND rails. All the
variant A layout rules still hold — star grounds (each INA219 and each bridge return runs
its own wire to the star), tight motor loops, C1/C2 at *every* bridge's power terminals,
I²C away from motor wiring.

### INA219 addressing

Solder jumpers on each module set the address:

| Door | A1 | A0 | Address |
|---|---|---|---|
| 1 | open | open | 0x40 |
| 2 | open | bridged | 0x41 |
| 3 | bridged | open | 0x44 |
| 4 | bridged | bridged | 0x45 |

Confirm with the boot log: the I²C scan must find all four addresses. Four modules also
mean four sets of 10 k bus pull-ups in parallel (≈ 2.5 k effective) — that is fine at
400 kHz; do not add the extra 4.7 k resistors from the variant A notes.

### Pin map (ESP32-S3-DevKitC-1)

| Door | IN1 (unlock) | IN2 (lock) | SW locked | SW unlocked | Button | INA219 |
|---|---|---|---|---|---|---|
| 1 | GPIO4 | GPIO5 | GPIO10 | GPIO11 | GPIO39 | 0x40 |
| 2 | GPIO6 | GPIO7 | GPIO12 | GPIO13 | GPIO40 | 0x41 |
| 3 | GPIO15 | GPIO16 | GPIO14 | GPIO21 | GPIO41 | 0x44 |
| 4 | GPIO17 | GPIO18 | GPIO1 | GPIO2 | GPIO42 | 0x45 |

Shared: **GPIO8** SDA · **GPIO9** SCL · **GPIO48** on-board WS2812 (older DevKitC-1
revisions route the LED to GPIO38 — change `pin_rgb` if yours does).

Avoided on purpose: GPIO0 / 3 / 45 / 46 (strapping), GPIO19 / 20 (USB),
GPIO43 / 44 (UART0), GPIO35 – 37 (used by octal-PSRAM boards). Position switches and
buttons are optional exactly as in variant A — unfitted pins float high on the internal
pull-up and read inactive.

### BOM delta

Quantities against the variant A BOM: U2 ×4, U3 ×4 (with address jumpers set), M1 ×4,
R1–R8 (eight 10 k pull-downs), C1/C2 ×4 (at each bridge), C3 ×4 (at each motor),
F1 becomes 5 A. U1 becomes an ESP32-S3-DevKitC-1 (any flash size; N8R2 is plenty).
One MH-MINI-360 still powers everything — the ESP plus four INA219s draw well under
its 1.8 A.

### Commissioning

Run the variant A commissioning sequence **once per door** — each door has its own six
threshold entities, jog buttons, and *use position switches* toggle, all prefixed
"Door 1…4" in Home Assistant. Doors with different actuators, strokes, or friction get
different thresholds; that is the point of keeping the config per door.

The fault event carries a `door` field, so one automation covers all four:

```yaml
automation:
  - alias: Any door lock fault
    trigger:
      - platform: event
        event_type: esphome.door_lock_fault
    action:
      - service: notify.mobile_app_phone
        data:
          title: "{{ trigger.event.data.door }}: {{ trigger.event.data.reason }}"
          message: >-
            While {{ trigger.event.data.direction }} —
            {{ trigger.event.data.peak_current }} A after
            {{ trigger.event.data.travel_ms }} ms
```

And "close all" is one service call:

```yaml
script:
  close_all_doors:
    sequence:
      - service: lock.lock
        target:
          entity_id:
            - lock.door_locks_door_1
            - lock.door_locks_door_2
            - lock.door_locks_door_3
            - lock.door_locks_door_4
```

---

## Firmware notes

Decisions in `door_lock_a.yaml` / `packages/door.yaml` that are easy to undo by accident:

- **No PWM on the bridge.** `output: gpio`, not `ledc`. Switching to PWM chops the current
  the shunt sees and breaks every threshold above.
- **Both inputs low means coast**, and the DRV8871 drops into low-power sleep after about a
  millisecond of it — what you want between moves on a battery. The brake state (both
  inputs high) is never used.
- **The fast current sensor is `internal: true`** and polled at 50 ms. Everything Home
  Assistant sees is a slower derived copy, so the API isn't flooded with 20 values a second.
- **A 500 ms watchdog interval** force-coasts the bridge if it is ever still energised well
  past `max travel time`, independently of the move script. Combined with R1/R2 holding the
  inputs down through reset, there is no state in which the actuator runs unattended.
- **Reversing after a jam is time-based** — it drives back out for as long as it drove in,
  capped at 4 s. That path has no stall detection of its own, deliberately: if the
  obstruction is on the retreat side too, you want the fault raised rather than an infinite
  shuffle.

---

## References

- [Waveshare ESP32-C3-Zero documentation](https://docs.waveshare.com/ESP32-C3-Zero)
- [ESP32-C3-Zero pinout reference](https://www.espboards.dev/esp32/esp32-c3-zero/)
- [DRV8871 breakout — Botland](https://botland.com.pl/sterowniki-silnikow-dc/7043-drv8871-jednokanalowy-sterownik-silnikow-45v36a-adafruit-3190-5904422335373.html)
- [INA219 module — Gotronik](https://www.gotronik.pl/ina219-dwukierunkowy-czujnik-pradu-z-szyna-i2c-p-5736.html)
