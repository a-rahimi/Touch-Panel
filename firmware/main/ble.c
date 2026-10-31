#include "ble.h"
#include <stdio.h>
#include <string.h>
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

/* BLE_SERVICE_UUID and BLE_POSITION_UUID, least significant byte first. */
static const ble_uuid128_t service_uuid = BLE_UUID128_INIT(
    0x0d, 0xa3, 0x71, 0xca, 0x8c, 0x0b, 0xd7, 0x82, 0x3d, 0x4c, 0x43, 0x95, 0x20, 0xb5, 0xbc, 0xd5);
static const ble_uuid128_t position_uuid = BLE_UUID128_INIT(
    0x0d, 0xa3, 0x71, 0xca, 0x8c, 0x0b, 0xd7, 0x82, 0x3d, 0x4c, 0x43, 0x95, 0x21, 0xb5, 0xbc, 0xd5);

static uint16_t position_handle;
static uint16_t conn = BLE_HS_CONN_HANDLE_NONE;
static bool subscribed;
static uint8_t own_addr_type;
static char last[24] = "";

static int on_access(uint16_t conn_handle, uint16_t attr_handle, struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    /* A read returns the last position sent. */
    return os_mbuf_append(ctxt->om, last, strlen(last)) == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
}

static const struct ble_gatt_svc_def services[] = {
    {.type = BLE_GATT_SVC_TYPE_PRIMARY,
     .uuid = &service_uuid.u,
     .characteristics = (struct ble_gatt_chr_def[]){
         {.uuid = &position_uuid.u,
          .access_cb = on_access,
          .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
          .val_handle = &position_handle},
         {0}}},
    {0}};

static int on_gap(struct ble_gap_event *event, void *arg);

static void advertise(void)
{
    struct ble_hs_adv_fields adv = {0}, rsp = {0};
    adv.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    adv.name = (const uint8_t *)BLE_NAME;
    adv.name_len = strlen(BLE_NAME);
    adv.name_is_complete = 1;
    ble_gap_adv_set_fields(&adv);
    /* The 128-bit service UUID does not fit beside the name, so it goes in the scan response. */
    rsp.uuids128 = &service_uuid;
    rsp.num_uuids128 = 1;
    rsp.uuids128_is_complete = 1;
    ble_gap_adv_rsp_set_fields(&rsp);
    struct ble_gap_adv_params params = {.conn_mode = BLE_GAP_CONN_MODE_UND, .disc_mode = BLE_GAP_DISC_MODE_GEN};
    ble_gap_adv_start(own_addr_type, NULL, BLE_HS_FOREVER, &params, on_gap, NULL);
}

static int on_gap(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (event->connect.status == 0)
            conn = event->connect.conn_handle;
        else
            advertise();
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        conn = BLE_HS_CONN_HANDLE_NONE;
        subscribed = false;
        advertise();
        break;
    case BLE_GAP_EVENT_SUBSCRIBE:
        if (event->subscribe.attr_handle == position_handle) subscribed = event->subscribe.cur_notify;
        break;
    case BLE_GAP_EVENT_ADV_COMPLETE:
        advertise();
        break;
    }
    return 0;
}

static void on_sync(void)
{
    ble_hs_util_ensure_addr(0);
    ble_hs_id_infer_auto(0, &own_addr_type);
    advertise();
}

static void host_task(void *arg)
{
    nimble_port_run();
    nimble_port_freertos_deinit();
}

void ble_start(void)
{
    nimble_port_init();
    ble_hs_cfg.sync_cb = on_sync;
    ble_svc_gap_init();
    ble_svc_gatt_init();
    ble_gatts_count_cfg(services);
    ble_gatts_add_svcs(services);
    ble_svc_gap_device_name_set(BLE_NAME);
    nimble_port_freertos_init(host_task);
}

void ble_report(float x_in, float y_in, int pad)
{
    snprintf(last, sizeof last, "%.2f,%.2f,%d", x_in, y_in, pad);
    if (conn == BLE_HS_CONN_HANDLE_NONE || !subscribed) return;
    struct os_mbuf *om = ble_hs_mbuf_from_flat(last, strlen(last));
    if (om) ble_gatts_notify_custom(conn, position_handle, om);
}

const char *ble_state(void)
{
    return conn == BLE_HS_CONN_HANDLE_NONE ? "advertising" : subscribed ? "subscribed" : "connected";
}
