#include <linux/module.h>
#include <linux/usb.h>
#include <linux/tty.h>
#include <linux/serial.h>
#include <linux/usb/serial.h>
#include <linux/printk.h>
#include <linux/kmod.h> // For request_module
#include <linux/gpio.h>   // For potential GPIO control if needed

#define HELTEC_VENDOR_ID  0x303A // Replace with actual VID
#define HELTEC_PRODUCT_ID 0x80C4 // Replace with actual PID

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("Driver for Heltec V3 Meshtastic device (enhanced serial association).");

static const struct usb_device_id heltec_table[] = {
    { USB_DEVICE(HELTEC_VENDOR_ID, HELTEC_PRODUCT_ID) },
    {} /* Terminating entry */
};
MODULE_DEVICE_TABLE(usb, heltec_table);

static int heltec_probe(struct usb_serial *serial, const struct usb_device_id *id)
{
    printk(KERN_INFO "heltec: Heltec V3 device (VID: 0x%04x, PID: 0x%04x) found.\n",
           id->idVendor, id->idProduct);

    /*
     * At this point, the device is associated with a serial port driver
     * (likely cdc_acm or another). We don't need to do much more here
     * in a simple model where the user-space daemon handles the Meshtastic
     * protocol over this serial port.
     *
     * In a more complex scenario, if the Heltec V3 required specific
     * initialization sequences over serial or GPIO control, that would
     * be implemented here using the 'serial' pointer and potentially
     * finding GPIO lines associated with the USB device (if exposed).
     */

    return 0;
}

static void heltec_disconnect(struct usb_serial *serial)
{
    printk(KERN_INFO "heltec: Heltec V3 device disconnected.\n");
}

static struct usb_serial_driver heltec_serial_driver = {
    .driver = {
        .owner = THIS_MODULE,
        .name = "heltec",
    },
    .id_table = heltec_table,
    .probe = heltec_probe,
    .disconnect = heltec_disconnect,
};

static int __init heltec_init(void)
{
    int retval;

    /*
     * We still try to load cdc_acm as it's a common driver.
     * The kernel will automatically use the appropriate serial driver
     * if one matches the device. Our driver here primarily serves to
     * specifically identify the Heltec V3 and log its connection.
     */
    if (request_module("cdc_acm") == 0) {
        printk(KERN_INFO "heltec: Loaded cdc_acm module.\n");
    } else {
        printk(KERN_INFO "heltec: cdc_acm module not loaded (may be loaded already or device uses a different serial driver).\n");
    }

    retval = usb_serial_register(&heltec_serial_driver);
    if (retval) {
        printk(KERN_ERR "heltec: Failed to register Heltec serial driver: %d\n", retval);
        return retval;
    }

    printk(KERN_INFO "heltec: Driver initialized.\n");
    return 0;
}

static void __exit heltec_exit(void)
{
    usb_serial_deregister(&heltec_serial_driver);
    printk(KERN_INFO "heltec: Driver unloaded.\n");
}

module_init(heltec_init);
module_exit(heltec_exit);
