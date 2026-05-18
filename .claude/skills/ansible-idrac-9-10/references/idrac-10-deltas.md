# iDRAC 9 → iDRAC 10 deltas

Verbatim extracts from the **iDRAC 10 Version 1.30.xx Series Attribute
Registry** (March 2026 / Rev A01), the upstream `dellemc.openmanage`
CHANGELOG, and the support matrix in `docs/README.md` of
`dell/dellemc-openmanage-ansible-modules` @ 10.0.2. Treat as paste-quality
reference — the rename tables in particular are what `idrac_attributes`
playbooks need to migrate.

## 1. Module support matrix — what works on which generation

(From `docs/README.md` lines 13-73 of dellemc.openmanage 10.0.2.)

### iDRAC 9 only (do NOT use on iDRAC 10)

| Module | What to use instead on iDRAC 10 |
|---|---|
| `idrac_network` | `idrac_network_attributes` (preferred) or `idrac_attributes` with Redfish names (`Network.1.DNSRacName`, `IPv4.1.StaticDNS1`, …) |
| `idrac_syslog` | `idrac_attributes` — `idrac_syslog` deprecated in 9.12.1, hard removal scheduled 2027-05-27 |
| `idrac_timezone_ntp` | `idrac_attributes` |
| `dellemc_configure_idrac_eventing` | `idrac_attributes` |
| `dellemc_configure_idrac_services` | `idrac_attributes` |
| `dellemc_idrac_lc_attributes` | `idrac_attributes` against `LifecycleController.*` |
| `dellemc_idrac_storage_volume` | `idrac_storage_volume` |
| `dellemc_system_lockdown_mode` | `idrac_attributes` against system-lockdown attribute |

### iDRAC 9 AND iDRAC 10 (preferred surface)

All other `idrac_*` and `redfish_*` modules:

- Auth / generation: `idrac_session`, `idrac_attributes`,
  `idrac_user`, `idrac_user_info`, `idrac_certificates`,
  `idrac_secure_boot`
- BIOS / boot / reset: `idrac_bios`, `idrac_boot`, `idrac_reset`,
  `idrac_diagnostics`, `idrac_system_erase`
- Firmware / lifecycle: `idrac_firmware` (OMSDK, no tokens),
  `idrac_firmware_info`, `idrac_lifecycle_controller_jobs`,
  `idrac_lifecycle_controller_job_status_info`,
  `idrac_lifecycle_controller_logs`,
  `idrac_lifecycle_controller_status_info`
- Network: `idrac_network_attributes`
- Storage: `idrac_storage_volume`, `idrac_redfish_storage_controller`,
  `redfish_storage_volume`, `redfish_firmware`,
  `redfish_firmware_rollback`
- Info / virtual: `idrac_system_info`, `idrac_virtual_media`,
  `redfish_powerstate`, `redfish_event_subscription`
- License / OS / SCP / support: `idrac_license`, `idrac_os_deployment`,
  `idrac_server_config_profile` (SCP — not yet qualified on iDRAC 10
  per upstream #959), `idrac_support_assist`

### iDRAC 8 (legacy)
Dropped in collection 10.0.0. Pin `dellemc.openmanage` 9.12.1 for
fleets that still contain iDRAC 8.

## 2. Auth / endpoint deltas at the Redfish layer

| Surface | iDRAC 9 | iDRAC 10 / 17G |
|---|---|---|
| Manager URI | `/redfish/v1/Managers/iDRAC.Embedded.1` | same |
| Jobs URI | `/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/{id}` | **`/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/{id}`** |
| Manager OEM attrs | `/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/iDRAC.Embedded.1` | same |
| SessionService | `/redfish/v1/SessionService/Sessions` (discovered via `/redfish/v1` `Links.Sessions`) | same |
| BasicAuth default | `Enabled` (< 7.30.10.50) → `Unadvertised` (≥ 7.30.10.50) | **`Unadvertised`** (≥ 1.30.10.50; XE branches lead) |
| WS-MAN | Supported | **Removed** — Redfish + RACADM + Web UI only |
| Default mgmt protocols | Redfish, WS-MAN, RACADM | Redfish, RACADM |

The dellemc modules dispatch automatically on `hw_model` (`"iDRAC 9"`
vs `"iDRAC 10"`) — see `get_server_generation()` and
`validate_idrac10_and_above()` in `plugins/module_utils/idrac_redfish.py`.
Raw `ansible.builtin.uri` calls against `/Managers/iDRAC.Embedded.1/Jobs/`
must conditionally append `/Oem/Dell/` on iDRAC 10.

### Open Server Manager → iDRAC 10 conversion (R670/R770)

On R670/R770 servers converted from Open Server Manager (OSM) to iDRAC 10,
an intermediate state may expose the manager as `bmc` instead of
`iDRAC.Embedded.1`:

```
/redfish/v1/Managers/bmc/EthernetInterfaces
```

The steady-state ID after conversion completes is `iDRAC.Embedded.1`.
KB 000240160. Discovery code that lists `/Managers/` and pins to the
first member name will be surprised.

## 3. Attribute registry — Deprecated groups & attributes (iDRAC 10)

From iDRAC 10 1.30.xx Attribute Registry, Chapter 2 (Table 1).
**Header text:** *"This section provides the list of attributes and
groups that are not available on 17G platforms."*

(17G = the PowerEdge generation that runs iDRAC 10.)

### Whole groups deprecated
- `iDRAC.ACME` (entire group)
- `iDRAC.CurrentNIC` (entire group)
- `iDRAC.CurrentIPv4` (entire group)
- `iDRAC.CurrentIPv6` (entire group)
- `iDRAC.GroupManager` — Group Manager features gone on 17G
- `iDRAC.IPv4Static` (replaced by `iDRAC.IPv4.Static*`)
- `iDRAC.IPv6Static` (replaced by `iDRAC.IPv6.Static*`)
- `iDRAC.RSM` — Remote Server Management gone
- `iDRAC.SCEP` (consolidated into `iDRAC.ACE`)
- `iDRAC.Telemetry.TelemetrySubscription1` through `…Subscription8`
- All `iDRAC.Telemetry*` legacy groups (`Aggregation`, `CPUMem`,
  `CPURegisters`, `CPUSensor`, `Fan`, `FCPortStatistics`, `FCSensor`,
  `FPGASensor`, `GPUMetrics`, `GPUStatistics`, `MemorySensor`,
  `NICSensor`, `NICStatistics`, `NVMeSMARTData`, `PowerMetrics`,
  `PowerStatistics`, `PSUMetrics`, `Sensor`, `SerialLog`,
  `StorageDiskSMARTData`, `StorageSensor`, `SystemUsage`,
  `ThermalMetrics`, `ThermalSensor`)
- `iDRAC.vFlashSD.*` — every vFlash SD attribute (`AvailableSize`,
  `Bitmap`, `Health`, `Initialized`, `Licensed`, `Presence`,
  `Signature`, `Size`, `WriteProtect`)
- `PSU.Info`
- `System.PSUSlot`
- `System.PSUSlotReq`

### Individual attributes deprecated
- `iDRAC.ActiveDirectory.RacDomain`
- `iDRAC.ActiveDirectory.RacName`
- `iDRAC.ActiveDirectory.Schema`
- `iDRAC.NIC.AutoNeg`
- `iDRAC.NIC.DiscoveryLldp`
- `iDRAC.NIC.DNSDomainFromDHCP`
- `iDRAC.NIC.DNSRegisterInterval`
- `iDRAC.NIC.Failover`
- `iDRAC.NIC.Selection`
- `iDRAC.NIC.TopologyLldp`
- `iDRAC.NICStatic.DNSDomainName`
- `iDRAC.OS-BMC.AdminState`
- `iDRAC.OS-BMC.OsIpAddress`
- `iDRAC.OS-BMC.PTMode`
- `iDRAC.OS-BMC.UsbNicIpv4AddressSupport`
- `iDRAC.OS-BMC.UsbNicULA`
- `iDRAC.Redfish.Enable` — Redfish toggle moved; use `BasicAuthState`
- `iDRAC.Users.MD5v3Key`
- `iDRAC.Users.SHA1v3Key`
- `iDRAC.Users.SHA256Password`
- `iDRAC.Users.SHA256PasswordSalt`
- `System.ServerPwr.PSRapidOn`
- `System.ServerPwr.RapidOnPrimaryPSU`

Playbooks that set any of these against iDRAC 10 will silently **no-op**
(Redfish does not error on unknown attribute keys in some Dell
implementations — it just ignores them and reports `changed: false`).

## 4. Attribute registry — Reorganized under new groups (iDRAC 10)

From Chapter 3 (Table 2). Header: *"The following attributes have been
moved under different groups in 17G."*

### Networking (the largest set)

| Deprecated (iDRAC 9) | New (iDRAC 10) |
|---|---|
| `iDRAC.IPv4Static.Address` | `iDRAC.IPv4.StaticAddress` |
| `iDRAC.IPv4Static.DNS1` / `.DNS2` / `.DNS3` | `iDRAC.IPv4.StaticDNS1` / `.StaticDNS2` / `.StaticDNS3` |
| `iDRAC.IPv4Static.Gateway` | `iDRAC.IPv4.StaticGateway` |
| `iDRAC.IPv4Static.Netmask` | `iDRAC.IPv4.StaticNetmask` |
| `iDRAC.IPv6.DUID` | `iDRAC.Network.DUID` |
| `iDRAC.IPv6Static.Address1` | `iDRAC.IPv6.StaticAddress1` |
| `iDRAC.IPv6Static.DNS1` / `.DNS2` / `.DNS3` | `iDRAC.IPv6.StaticDNS1` / `.StaticDNS2` / `.StaticDNS3` |
| `iDRAC.IPv6Static.Gateway` | `iDRAC.IPv6.StaticGateway` |
| `iDRAC.IPv6Static.PrefixLength` | `iDRAC.IPv6.StaticPrefixLength` |
| `iDRAC.NIC.AutoConfig` | `iDRAC.Network.AutoConfig` |
| `iDRAC.NIC.DiscoveryLLDP` | `iDRAC.Network.DiscoveryLLDP` |
| `iDRAC.NICStatic.DNSDomainName` | `iDRAC.Network.StaticDNSDomainName` |
| `iDRAC.NIC.DNSDomainNameFromDHCP` | `iDRAC.Network.DNSDomainNameFromDHCP` |
| `iDRAC.NIC.DNSRacName` | `iDRAC.Network.DNSRacName` |
| `iDRAC.NIC.DNSRegister` | `iDRAC.Network.DNSRegister` |
| `iDRAC.NIC.DNSRegisterInterval` | `iDRAC.Network.DNSRegisterInterval` |
| `iDRAC.NIC.TopologyLldp` | `iDRAC.Network.TopologyLLDP` |
| `iDRAC.CurrentNIC.ActiveNIC` | `iDRAC.NIC.ActiveNIC` |
| `iDRAC.CurrentNIC.LinkStatus` | `iDRAC.NIC.LinkStatus` |

**Pattern:** static IP attrs collapsed `iDRAC.IPv4Static.X` →
`iDRAC.IPv4.StaticX`; runtime/discovery NIC attrs moved to a new
`iDRAC.Network.*` group; the surviving `iDRAC.NIC.*` group keeps only
hardware-NIC selectors.

### Certificate enrollment — ACME + SCEP consolidated under ACE

| Deprecated (iDRAC 9) | New (iDRAC 10) |
|---|---|
| `iDRAC.ACME.CA-URL` | `iDRAC.ACE.CA-URL` |
| `iDRAC.ACME.EnrollmentAction` | `iDRAC.ACE.EnrollmentAction` |
| `iDRAC.ACME.EnrollmentStatus` | `iDRAC.ACE.EnrollmentStatus` |
| `iDRAC.SCEP.CA-URL` | `iDRAC.ACE.CA-URL` |
| `iDRAC.SCEP.ChallengePassword` | `iDRAC.ACE.ChallengePassword` |
| `iDRAC.SCEP.Enable` | `iDRAC.ACE.Enable` |
| `iDRAC.SCEP.EnrollmentAction` | `iDRAC.ACE.EnrollmentAction` |
| `iDRAC.SCEP.EnrollmentStatus` | `iDRAC.ACE.EnrollmentStatus` |

Both ACME and SCEP cert-enrollment surfaces fold into a single new
`iDRAC.ACE` group. `CA-URL`, `EnrollmentAction`, and
`EnrollmentStatus` are the surviving common keys.

### BIOS power-recovery moves out of BIOS

| Deprecated (iDRAC 9) | New (iDRAC 10) |
|---|---|
| `BIOS.SysSecurity.AcPwrRcvry` | `System.ServerPwr.AcPwrRcvry` |
| `BIOS.SysSecurity.AcPwrRcvryDelay` | `System.ServerPwr.AcPwrRcvryDelay` |
| `BIOS.SysSecurity.AcPwrRcvryUserDelay` | `System.ServerPwr.AcPwrRcvryUserDelay` |

`idrac_bios` recipes that set these three values must migrate the
declaration into `idrac_attributes` targeting `System.ServerPwr.*`.

## 5. Attribute registry — Changed values, enums, defaults (iDRAC 10)

From Chapter 4 (Table 3). Header: *"The following table lists the
impacted attributes with their changes."*

| Attribute | Change |
|---|---|
| `iDRAC.Info.ServerGen` | Possible values changed: `12G=1, 13G=2, 14G=3, 15G=4, 16G=5, 17G=6, 18G=7` |
| `iDRAC.Info.Type` | New byte enums incl. `17G Monolithic=96, 17G Modular=97, 17G DCS=98, 18G=112/113/114` |
| `iDRAC.IPMISerial.BaudRate` | Default changed to **115200** (was 57600) |
| `iDRAC.IPMISerial.FlowControl` | Default changed to `0` |
| `iDRAC.Serial.BaudRate` | Default changed to **115200** |
| `iDRAC.NIC.Speed` | Possible values now: `10;100;1000;2500;10000;20000;25000;40000;50000;100000;200000;400000;800000` (gained 200/400/800 G) |
| `iDRAC.NTPConfigGroup.NTP1SecurityType` | Possible values **narrowed** to `Disabled;SHA384;SHA512` (SHA1/MD5 removed) |
| `iDRAC.NTPConfigGroup.NTP2SecurityType` | same |
| `iDRAC.NTPConfigGroup.NTP3SecurityType` | same |
| `iDRAC.PlatformCapability.NICRoTCapable` | Default changed to `0` |
| `iDRAC.SEKM.AutoSecure` | Now Platform Dependent |
| `iDRAC.ServiceModule.NetworkConnection` | Now Read+Write (was read-only) |
| `iDRAC.ServiceModule.SoftwareRAIDSupported` | Now Read+Write (was read-only) |
| `iDRAC.SPDM.DeviceList` | Default device list changed (long enum) |
| `LifecycleController.LCAttributes.PartFirmwareUpdate` | Now Platform Dependent |
| `System.ServerPwr.RebootlessPsuFwUpdate` | Now Platform Dependent |

### Implication: idempotence checks break

Any playbook that asserts the **old** default (57600 baud, SHA1 NTP
security, etc.) and bails on mismatch will now flag a "drift" on first
contact with an iDRAC 10. Either update the assertions to the new
defaults, or move the assertion to a `when: is_idrac9` branch.

## 6. Net-new attributes in iDRAC 10 firmware 1.30.10.50

From the Attribute Registry intro [p.4]:

- `BIOS.IntegratedDevices.AcpiConsistentNicName` — new BIOS attribute
- `IDRAC.Redfish.BasicAuthState` — **the** new attribute behind the
  `Enabled`/`Unadvertised`/`Disabled` tri-state covered in
  `auth-and-session.md`
- `LifecycleController.LCAttributes.UpdateNotification`

## 7. Per-module iDRAC 10 quirks (from collection CHANGELOG known-issues)

These persist through 10.0.2:

| Module | Quirk on iDRAC 10 |
|---|---|
| `idrac_attributes` | `SNMP.1.AgentCommunity` accepts both string AND integer (was string-only on iDRAC 9) |
| `idrac_redfish_storage_controller` | `PatrolReadRatePercent` cannot be set |
| `redfish_storage_volume` | `encryption_type` and `block_io_size_bytes` are read-only (both 9 and 10 — module ignores them) |
| `idrac_license` | Different error wording across generations for invalid share name |
| `idrac_server_config_profile` | SCP not yet qualified on iDRAC 10 (#959) — use per-attribute modules until then |

## 8. PowerEdge 17G platform map (iDRAC 10 hardware)

Rack:
- R170, R270, R370, R470, R570
- R670 (+xs variants)
- R770 (+xs, +xa variants)
- R870, R970

Multi-node / dense:
- R6715, R6725, R7715, R7725

HPC:
- C6715, C7715

Modular:
- M7725

Accelerator XE (these ship with separate firmware branches that lead
the mainline):
- XE9780 (firmware branch 1.20.55.x)
- XE9785 (firmware branch 1.20.95.x)
- XE7740

Everything 16G and below stays on iDRAC 9 (7.x series).
Identifying gen: KB 000137343 (`/etc/dell-server-info` on RHEL/SLES;
or `dmidecode -t system | grep Product`; or
`racadm getsysinfo | grep -i model`; or the Redfish
`Info.1.HWModel` attribute).

## 9. Catalog and firmware updates

Unchanged on 17G — catalog still at:

- `https://downloads.dell.com/catalog/Catalog.gz`
- `https://downloads.dell.com/catalog/Catalog.xml.gz`
- with `.sha512.sign` signature files

DUP-bundle format is the same as 14G/15G/16G, so `update_url` patterns
in `idrac_firmware` / `redfish_firmware` playbooks keep working.

What **did** change: the F10 Lifecycle Controller TUI menu was removed
from 17G's boot picker. The iDRAC update service still works the
same — module behavior unchanged — but operators looking for the
familiar LC menu post-boot will find it gone.
