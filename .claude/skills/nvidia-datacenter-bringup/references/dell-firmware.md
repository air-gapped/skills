# Dell HGX B300 baseboard firmware

Step 0 of B300 bring-up on a Dell PowerEdge XE9780 / XE9785 chassis. Baseboard firmware below v1.4.30 (March 2026) burns hours chasing OS-side problems whose root cause is firmware.

## Why this matters

NVIDIA `nvidia-smi` reports no GPUs, fabricmanager fails to find the CX bridge, NVLink hangs under load — all of these have been observed on B300 chassis running firmware below v1.4.30. The fixes are in firmware, not in the OS. Always update firmware BEFORE debugging driver or fabricmanager issues.

## Required firmware

**Dell HGX B300 SXM6 air-cooled baseboard firmware v1.4.30** (March 25, 2026).

Components updated in this bundle (verbatim from the release notes — full text in [[b300-firmware-release-notes]]):

| Component | Version after v1.4.30 |
|---|---|
| FW (top-level) | 1.4.30 |
| ERoT | 01.04.0046.0000_n04 |
| FPGA | 1.54 |
| HMC | B3-2511-04.0 |
| GPU VBIOS | 97.10.64.00.0C (air-cooled) / 97.10.64.00.0A (partner-cooled) |
| SMA GPU | 0004.00.0272.0000 |
| **ConnectX-7 NVSwitch Bridge** | **28.47.2526** |
| NVSwitch | 35_2014_4770 |
| **ConnectX-8 PCIe Switch** | **40.47.2526** |
| SMA ConnectX-8 | 0011.00.0272.0002 |

The bolded ones are what fabricmanager actually talks to through the CX bridge architecture.

## Bug fixes in v1.4.30

> - Fixed the issue where NVLink Task Scheduling behavior was leading to GPU driver hangs
> - Fixed the issue where Embedded ConnectX-8 devices do not stably enumerate on MCTP
> - Other minor bug fixes and enhancements

And from v1.4.00:
> - Fixed the issue where multiple CX-8 failed to initialize after a warm reboot
> - Fixed the issue where pcie downstream device detection failed
> - Fixed the issue of NCCL performance was reduced due to incorrect power profile of NVSwitch

The "Embedded ConnectX-8 devices do not stably enumerate on MCTP" fix is the one most likely to explain "nvidia-smi sees no GPUs" symptoms on first bring-up. On a host below v1.4.30 with missing GPUs, this is almost certainly the root cause.

## Download

- Air-cooled: https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=xrg43
- Partner-cooled: https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=662gc
- Release notes text: https://dl.dell.com/FOLDER14346751M/3/Release-notes.txt

## Update procedure via iDRAC

The release notes' install instructions, verbatim:

```
1. Download the file to a system with access to the iDRAC of the server you wish to update.
2. Log into the iDRAC of the server you wish to update.
3. Navigate to the System Update menu.
4. Click the Browse button and navigate to the downloaded file and select.
5. Click the check box next to the package at the bottom of the iDRAC menu.
6. Click the Update button in the iDRAC menu.
7. Wait for the created Job to finish.
8. AC Reboot or Virtual AC Power Cycle the system.
```

Steps 1–7 are standard. **Step 8 is where everyone gets stuck.**

## The critical AC-cycle gotcha

Release notes warning, verbatim:

> Note: Invoking a Virtual AC cycle through **BIOS Full Power Cycle may not activate all GPU assembly firmware components.**

Translation: the iDRAC web-UI "Full Power Cycle" button doesn't reliably propagate to the GPU baseboard. The firmware update job reports "success" but the new firmware doesn't take effect — sometimes for the GPU baseboard, sometimes for the CX bridge, sometimes partially. The failure is visible when `FirmwareInventory` is checked after the cycle and the versions haven't moved.

**Cure**: use `DellOemChassis.ExtendedReset`, NOT `Chassis.Reset FullPowerCycle`. Per Dell KB 000355295.

## Reliable activation: two-step Redfish (Dell OEM)

```bash
# Variables
IDRAC=10.0.0.10
USER=root
PWD=calvin

# Step 1: graceful shutdown
curl -k -u "$USER:$PWD" -X POST \
  "https://$IDRAC/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset" \
  -H "Content-Type: application/json" \
  -d '{"ResetType":"GracefulShutdown"}'

# Wait for graceful shutdown to complete (poll PowerState)
while [ "$(curl -k -s -u "$USER:$PWD" "https://$IDRAC/redfish/v1/Systems/System.Embedded.1" | jq -r .PowerState)" != "Off" ]; do
  echo "Waiting for graceful shutdown..."
  sleep 5
done

# Step 2: Dell OEM extended reset (the magic that activates baseboard firmware)
curl -k -u "$USER:$PWD" -X POST \
  "https://$IDRAC/redfish/v1/Chassis/System.Embedded.1/Actions/Oem/DellOemChassis.ExtendedReset" \
  -H "Content-Type: application/json" \
  -d '{"ResetType":"PowerCycle","FinalPowerState":"On"}'
```

## Reliable activation: single-call alternative

The release notes also document a single Redfish call that works in some iDRAC versions:

```bash
curl -k -u "$USER:$PWD" -X POST \
  "https://$IDRAC/redfish/v1/Chassis/System.Embedded.1/Actions/Chassis.Reset" \
  -H "Content-Type: application/json" \
  -d '{"ResetType":"FullPowerCycle"}'
```

Dell KB 000355295 indicates the `DellOemChassis.ExtendedReset` two-step is the supported recipe. The single-call `Chassis.Reset FullPowerCycle` works on newer iDRAC firmware but not reliably — Dell engineering called this out. Prefer the two-step.

## Reliable activation: physical AC pull

If neither Redfish path works (older iDRAC firmware, network issues), pull all power cords from both PSUs, wait 30 seconds, plug back in.

> Physical AC Cycle requires that all AC power is removed from the server node.
> https://www.dell.com/support/kbdoc/en-us/000175625/

This is always reliable but requires physical access.

## Verify activation via Redfish

Before and after the AC cycle, dump the FirmwareInventory:

```bash
curl -k -u "$USER:$PWD" \
  "https://$IDRAC/redfish/v1/UpdateService/FirmwareInventory" | jq '.Members[].\"@odata.id\"'

# Then for each entry of interest:
curl -k -u "$USER:$PWD" \
  "https://$IDRAC/redfish/v1/UpdateService/FirmwareInventory/HGX_FW_GPU_SXM_1" | jq .

# Or use Dell's reference Python script:
# https://github.com/dell/iDRAC-Redfish-Scripting/blob/master/Redfish%20Python/GetFirmwareInventoryREDFISH.py
```

Diff the Version fields before and after. If anything didn't move to v1.4.30 levels, the activation didn't take.

## Air-gapped iDRAC access

Even with no uplink, iDRAC's host-side has a link-local interface at `169.254.0.17` that the OS can reach through the BMC USB-NIC. Redfish API works over this. No DNS, no external dependencies.

```bash
# From inside the host OS, after install
ip -4 addr | grep '169.254'
# Look for an interface (usually idrac or bmc) with 169.254.x.x

curl -k -u <user>:<pass> https://169.254.0.17/redfish/v1/UpdateService/FirmwareInventory
```

## Known follow-up issue (post-flash)

From the v1.4.30 release notes, Known Issues section:

> - ConnectX-8 firmware update as part of the GPU assembly firmware update **might fail**. Power cycle and apply the firmware update.

Meaning: after the first AC cycle, the CX-8 may not have taken the new firmware. The remedy is to re-run the exact same DUP/firmware-update flow — the second pass picks up the components that missed the first activation window.

In practice: do the update + AC cycle, then run `FirmwareInventory` and diff. If CX-8 version didn't move, repeat the firmware-update flow and AC-cycle once more.

## Dell DUP misidentification (KB 000377140)

> DUP firmware updates for NVIDIA ConnectX adapters fail on B200/B300 hosts with "This Update Package is not compatible with your system configuration" because embedded CX ASICs in the GPU assembly confuse DUP inventory.

On the standalone CX-8 NIC firmware updater (not the GPU baseboard bundle):

```bash
# Extract the DUP
chmod +x <DUP_file>.BIN
./<DUP_file>.BIN --extract /tmp/dup-payload

# Run mlxfwmanager directly, bypassing DUP's inventory check
sudo mlxfwmanager -u -D /tmp/dup-payload -y
```

This is also documented in KB 000377140: https://www.dell.com/support/kbdoc/en-us/000377140/

## Non-Dell vendor pointers

This skill is Dell-primary. For other chassis vendors:

- **Supermicro NVIDIA HGX B300**: AOC update bundles via SUM (Super Update Manager) / BMC. See Supermicro datasheet `SuperCluster_B300_Front_IO.pdf`. Similar AC-cycle requirement.
- **HPE Cray EX**: SAT (System Admin Toolkit) / FAS (Firmware Action Service) firmware streams. Documentation lives in HPE Cray support portal.
- **Lenovo ThinkSystem SR685a**: XCC (XClarity Controller) / OneCLI bundles. Same AC-cycle class requirement on GPU baseboard.

All three need an AC-class power cycle after GPU baseboard flash; none of them use Dell's `DellOemChassis.ExtendedReset` (it's Dell-OEM-only). The general pattern is: GPU baseboard firmware components need full-chassis AC, BMC-mediated soft resets are insufficient.

## References

- Release notes: https://dl.dell.com/FOLDER14346751M/3/Release-notes.txt (verbatim in [[b300-firmware-release-notes]])
- Air-cooled driver details: https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=xrg43
- Partner-cooled driver details: https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=662gc
- KB on AC-cycle reliability: https://www.dell.com/support/kbdoc/en-us/000355295/
- KB on DUP misidentification: https://www.dell.com/support/kbdoc/en-us/000377140/
- Physical AC drain procedure: https://www.dell.com/support/kbdoc/en-us/000175625/
- Dell Redfish scripting examples: https://github.com/dell/iDRAC-Redfish-Scripting
- NVIDIA DGX B300 FW guide (component class baseline): https://docs.nvidia.com/dgx/dgxb300-fw-update-guide/
