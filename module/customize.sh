[ "$(uname -r)" = 4.14.336-Nethunter-CDC-KSU-g020784b3a0ae ] ||
    abort "Install the matching Narzo 20 CDC kernel first."
(cd "$MODPATH" && sha256sum -c SHA256SUMS) || abort "Module checksum verification failed."
for field in host_addr dev_addr; do
    saved=/data/adb/modules/narzo20_cdc/$field
    [ ! -s "$saved" ] || cp "$saved" "$MODPATH/$field" ||
        abort "Could not preserve the USB MAC address."
done
ui_print "NCM will replace the USB tethering profile; ADB stays available."
