#!/system/bin/sh
MODDIR=${0%/*}
[ "$(uname -r)" = 4.14.336-Nethunter-CDC-KSU-g020784b3a0ae ] || exit 0
umask 077
exec >> "$MODDIR/service.log" 2>&1
. "$MODDIR/gadget.sh"
echo "Starting Narzo CDC service"
for module in 88XXau 8188eu 88x2bu; do
    if ! grep -q "^$module " /proc/modules; then
        insmod "$MODDIR/lib/$module.ko" || echo "Failed to load $module"
    fi
done
while [ "$(getprop sys.boot_completed)" != 1 ]; do sleep 2; done
trap 'restore_gadget' EXIT
trap 'exit 0' INT TERM
active=0
failed_profile=
while [ ! -e "$MODDIR/disable" ] && [ ! -e "$MODDIR/remove" ]; do
    profile=$(getprop sys.usb.config)
    if ! is_tether_profile "$profile"; then
        if [ "$active" = 1 ] || [ -d "$N" ]; then
            restore_gadget || { echo "USB cleanup failed"; exit 1; }
        fi
        active=0
        failed_profile=
    elif is_link ncm.narzo; then
        active=1
    elif [ "$profile" != "$failed_profile" ] &&
            [ "$(getprop sys.usb.state)" = "$profile" ] &&
            is_link rndis.gs4; then
        if apply_gadget; then
            active=1
            echo "NCM active with $profile"
        else
            echo "NCM activation failed; restoring original USB"
            restore_gadget || exit 1
            active=0
            failed_profile=$profile
        fi
    fi
    sleep 2
done
