# Dell HGX B300 SXM6 270GB 8-GPU Air-Cooled — Firmware v1.4.30 Release Notes

> Retrieved 2026-05-21 via `curl -A 'Mozilla/5.0' https://dl.dell.com/FOLDER14346751M/3/Release-notes.txt` (WebFetch returns 403; curl with a browser user-agent works).
>
> Verbatim — formatting preserved as plain text. The skill's recipe quotes the AC-cycle warning and the Redfish curl commands from this file.
>
> **Substitution note:** Dell's original text uses `root:calvin` in the `example:` curl lines — that's iDRAC's documented factory-default credential pair. The text below substitutes `<user>:<pass>` to satisfy gitleaks default-rule scanning. Operators should rotate the iDRAC password during chassis commissioning regardless; running production with factory defaults is itself the bug.

---

```
#####################################################################
#	Dell Technologies Inc
#	Nvidia HGX B300 SXM6 270GB 8-GPU Air-Cooled Release Notes
#	March 25, 2026
#
#	RELEASE Version v1.4.30
#####################################################################

Hardware Compatibility
======================
This release of software supports the following hardware:
- Nvidia HGX B300 SXM6 270GB 8-GPU Air-Cooled Baseboard Assembly

Firmware versions
===================
Version 20.26.03.25 - FW 1.4.30

ERoT                        01.04.0046.0000_n04
FPGA                        1.54
HMC                         B3-2511-04.0
GPU VBIOS                   97.10.64.00.0C
SMA GPU                     0004.00.0272.0000
ConnectX-7 NVSwitch Bridge  28.47.2526
NVSwitch                    35_2014_4770
ConnectX-8 PCIe Switch      40.47.2526
SMA ConnectX-8              0011.00.0272.0002

Release Contents
===================
Nvidia HGX B300 SXM6 270GB 8-GPU Air-Cooled Firmware installer for use in iDRAC

* Third-party trademarks and copyrights are the property of their respective owners.

Important Information
===================
- IMPORTANT: The system must be Powered ON for the firmware update to be applied.
- An AC REBOOT or Redfish initiated Virtual AC Power Cycle is required after completion for the firmware changes to take effect.
- Please review the Virtual AC options in the installation instructions
- Power Smoothing feature is not implemented or supported

New Feature Summary 
===================
- None

Fixes in FW 1.4.30
===================
- Fixed the issue where NVLink Task Scheduling behavior was leading to GPU driver hangs
- Fixed the issue where Embedded ConnectX-8 devices do not stably enumerate on MCTP
- Other minor bug fixes and enhancements

Fixes included from FW 1.4.00
=============================
- Fixed the issue where multiple CX-8 failed to initialize after a warm reboot
- Fixed the issue where pcie downstream device detection failed
- Fixed the issue of NCCL performance was reduced due to incorrect power profile of NVSwitch

Known Issues
===================
- GPU assembly firmware activation after updating needs to be done through a physical AC cycle or through a Redfish initiated Virtual AC Cycle
- ConnectX-8 firmware update as part of the GPU assembly firmware update might fail.  Power cycle and apply the firmware update.

Installation Instructions
=========================
Installation via iDRAC.
1. Download the file to a system with access to the IDRAC of the server you wish to update.
2. Log into the iDRAC of the server you wish to update.
3. Navigate to the System Update menu.
4. Click the Browse button and navigate to the downloaded file and select.
5. Click the check box next to the package at the bottom of the IDRAC menu.
6. Click the Update button in the iDRAC menu.
7. Wait for the created Job to finish.
8. AC Reboot or Virtual AC Power Cycle the system.

Physical AC Cycle requires that all AC power is removed from the server node
   https://www.dell.com/support/kbdoc/en-us/000175625/how-do-i-reset-and-drain-power-of-my-dell-poweredge-server


Initiating Virtual AC cycle from a remote host
==============================================
   Step 1: Initiate a graceful shutdown. It can be implemented by the following Redfish curl command
      curl -k -u ${username}:${pwd} -X POST https://${IDRAC_IP}/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset -H "Content-Type: application/json" -d '{"ResetType":"GracefulShutdown"}'

      example: curl -k -u <user>:<pass> -X POST https://10.0.0.10/redfish/v1/Systems/System.Embedded.1/Actions/ComputerSystem.Reset -H "Content-Type: application/json" -d '{"ResetType":"GracefulShutdown"}'


   Step 2: Initiate a virtual power cycle execution by the following Redfish curl command

      curl -k -u  ${username}:${pwd} -X POST https://${IDRAC_IP}/redfish/v1/Chassis/System.Embedded.1/Actions/Chassis.Reset -H "Content-Type: application/json" -d '{"ResetType": "PowerCycle", "FinalPowerState": "On"}'

      example: curl -k -u <user>:<pass> -X POST https://10.0.0.10/redfish/v1/Chassis/System.Embedded.1/Actions/Chassis.Reset -H "Content-Type: application/json" -d '{"ResetType": "PowerCycle", "FinalPowerState": "On"}'

Single Redfish command implementation:

      curl -k -u ${username}:${pwd} -X POST https://${IDRAC_IP}/redfish/v1/Chassis/System.Embedded.1/Actions/Chassis.Reset -H "Content-Type: application/json" -d '{"ResetType":"FullPowerCycle"}'

      example: curl -k -u <user>:<pass> -X POST https://10.0.0.10/redfish/v1/Chassis/System.Embedded.1/Actions/Chassis.Reset -H "Content-Type: application/json" -d '{"ResetType":"FullPowerCycle"}'


Note: Invoking a Virtual AC cycle through BIOS Full Power Cycle may not activate all GPU assembly firmware components.
```

---

## Skill-author cross-reference

- The "BIOS Full Power Cycle may not activate all GPU assembly firmware components" warning is the gotcha that wastes hours. The skill's recommended path is the two-step Redfish (graceful shutdown + `Chassis.Reset PowerCycle`), or equivalently the single `Chassis.Reset FullPowerCycle`. Dell KB 000355295 documents that some iDRAC versions need the OEM-specific `DellOemChassis.ExtendedReset` instead. See [[dell-firmware]] for the operational drill-down.

- The "ConnectX-8 firmware update as part of the GPU assembly firmware update might fail" known issue means: after the first AC cycle, query FirmwareInventory and diff. If CX-8 version didn't change, re-run the same DUP/firmware-update flow and AC-cycle again.

- For the partner-cooled chassis variant the equivalent release notes ID is `FOLDER14346756M` (driver ID `662gc`) with GPU VBIOS 97.10.64.00.0A.
