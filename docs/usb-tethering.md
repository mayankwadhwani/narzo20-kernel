# NCM tethering module

`Narzo20-CDC-KSU-module.zip` requires
`4.14.336-Nethunter-CDC-KSU-g020784b3a0ae`. Install it in KernelSU Next 3.2.0
and reboot. It is a script-only module; no overlay filesystem or metamodule is
required. The normal Android USB tethering switch selects NCM while retaining
ADB when USB debugging is enabled.

Keep both the manager and `ksud` on **3.2.0**. Manager 3.4.2 replaces the daemon
with an API-5 version that cannot install modules against this legacy API-0
kernel. A newer manager alone does not update the embedded root driver.

The service loads the three matching Realtek modules, then watches the normal
`rndis` and `rndis,adb` USB profiles. It does not select tethering automatically
when another USB mode is requested. It preserves its first MAC pair across
boots. Logs are in `/data/adb/modules/narzo20_cdc/service.log`.

## Why the network interface is still called rndis0

The USB function is `ncm.narzo`, and macOS attaches `AppleUSBNCMControl` and
`AppleUSBNCMData`. The Linux interface name does not determine the USB protocol.

This ROM selects only the first matching USB network interface for tethering.
Its Ethernet client also claims an interface named `usb0` and removes the
tethering IPv4 address. The module temporarily renames the unused RNDIS
interface, gives the NCM interface the name `rndis0`, and reconnects the gadget.
Android then supplies DHCP, DNS and forwarding through its own tethering
service. Turning tethering off removes the NCM function and restores the
original interface name where the original function still exists.

## Mac service priority

macOS creates a network service named `RMX2020`. Put it **below Wi-Fi** in
System Settings → Network → Set Service Order if Wi-Fi should remain the normal
internet connection. A higher-priority USB service can take over routing and
interrupt traffic while the phone or USB configuration restarts.

The module changes the phone only; it does not change Mac network priorities,
VPN settings or firewall rules. Leave the Mac service inactive when it is not
wanted. Native NCM requires no third-party Mac driver.

## Validation and removal

On the tested Narzo 20, the Mac obtained a DHCP lease, resolved DNS through the
phone, and completed HTTPS with traffic explicitly bound to the NCM interface.
Reboot autoloading, the normal Settings tethering switch and KernelSU disable
rollback were also verified. Wi-Fi remained the Mac default while USB worked
as a secondary connection. This does not verify
physical external wireless adapters, monitor mode or injection.

Disable or uninstall `narzo20_cdc` in KernelSU to restore the original USB
configuration. The service observes the disable/remove marker and restores its
gadget; rebooting also clears the volatile configuration. The wireless drivers
already loaded remain resident until reboot.

An older rollback kernel is left untouched because the service checks the
exact kernel release before loading drivers or changing USB.

To package already downloaded full-kernel artifacts locally:

```sh
python3 scripts/package_module.py /path/to/verified-kernel-artifacts
```
