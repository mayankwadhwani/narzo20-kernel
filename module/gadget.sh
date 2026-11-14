#!/system/bin/sh

G=/config/usb_gadget/g1
C=$G/configs/b.1
R=$G/functions/rndis.gs4
N=$G/functions/ncm.narzo

is_tether_profile() {
    case "$1" in rndis|rndis,adb) return 0 ;; *) return 1 ;; esac
}

is_link() {
    case "$(readlink "$C/f1")" in */"$1") return 0 ;; *) return 1 ;; esac
}

bind_udc() {
    # Android init can rebind the same configuration when ADB becomes ready.
    [ "$(cat "$G/UDC")" = musb-hdrc ] || echo musb-hdrc > "$G/UDC"
}

restore_names() {
    if [ -d /sys/class/net/cdc_rndis ] && [ ! -d /sys/class/net/rndis0 ]; then
        ip link set cdc_rndis down &&
            ip link set cdc_rndis name rndis0
    fi
}

restore_gadget() {
    if is_link ncm.narzo || {
        [ -d "$N" ] && [ ! -e "$C/f1" ] && [ ! -L "$C/f1" ] &&
            is_tether_profile "$(getprop sys.usb.config)"
    }; then
        { [ -z "$(cat "$G/UDC")" ] || echo "" > "$G/UDC"; } || return 1
        rm -f "$C/f1" || return 1
        rmdir "$N" || return 1
        restore_names || return 1
        if is_tether_profile "$(getprop sys.usb.config)"; then
            if [ ! -e "$C/f1" ]; then
                [ -d "$R" ] || return 1
                ln -s "$R" "$C/f1" || return 1
            fi
            sleep 2
            is_link rndis.gs4 && bind_udc || return 1
        fi
    else
        # An ordinary USB profile change already removed our configuration link.
        [ ! -d "$N" ] || rmdir "$N" || return 1
        restore_names || return 1
    fi
}

apply_gadget() {
    profile=$(getprop sys.usb.config)
    is_tether_profile "$profile" || return 1
    [ "$(getprop sys.usb.state)" = "$profile" ] || return 1
    [ "$(cat "$G/UDC")" = musb-hdrc ] || return 1
    is_link rndis.gs4 || return 1
    if [ "$profile" = rndis,adb ]; then
        [ "$(getprop sys.usb.ffs.ready)" = 1 ] || return 1
        case "$(readlink "$C/f2")" in */ffs.adb) ;; *) return 1 ;; esac
    fi
    [ -d /sys/class/net/rndis0 ] && [ ! -d /sys/class/net/cdc_rndis ] || return 1
    [ ! -d "$N" ] || return 1
    mkdir "$N" || return 1
    # Keep the first MAC pair across boots to avoid new Mac network services.
    for field in host_addr dev_addr; do
        if [ ! -s "$MODDIR/$field" ]; then
            cat "$R/$field" > "$MODDIR/$field" || return 1
        fi
        cat "$MODDIR/$field" > "$N/$field" || return 1
    done
    echo "" > "$G/UDC" &&
        rm "$C/f1" &&
        ip link set rndis0 down &&
        ip link set rndis0 name cdc_rndis &&
        ln -s "$N" "$C/f1" || return 1
    sleep 2
    [ "$(getprop sys.usb.config)" = "$profile" ] || return 1
    bind_udc || return 1
    # This ROM's Ethernet client claims usb0; rndis0 belongs only to tethering.
    ip link set usb0 down &&
        ip link set usb0 name rndis0 &&
        echo "" > "$G/UDC" || return 1
    sleep 2
    [ "$(getprop sys.usb.config)" = "$profile" ] || return 1
    bind_udc && is_link ncm.narzo
}
