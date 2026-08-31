import asyncio
from datetime import datetime, timezone

from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

# ----------------------- CONFIGURATION -----------------------
PC_IP = "192.168.1.207"
MODBUS_PORT = 502
DEVICE_ID = 1

# PLC -> Python
Ntp_reg_group = 100
Ntp_reg_Nb = 9

# Command sent by PLC if NTP sync has failed 5 times
Request_PC_TimeStamp = 1010

# Python -> PLC
PC_DateTime_reg_group = 200
PC_DateTime_reg_Nb = 8


# ----------------------- Define a asynchronous function to use function 'await' -----------------------
async def main():

    # Allocate register memory from 0 to 999
    device = SimDevice(
        DEVICE_ID,
        SimData(
            address=0,
            datatype=DataType.UINT16,
            values=[0] * 1000 
        )
    )

    # Create one Modbus TCP server
    server = ModbusTcpServer(
        device,
        address=(PC_IP, MODBUS_PORT)
    )

    print("-------------------------------------------")
    print("ABB PLC -> Python Modbus TCP Server")
    print("-------------------------------------------")
    print(f"Listening on port {MODBUS_PORT}")
    print(f"Device ID: {DEVICE_ID}")
    print("Waiting for PLC data...")
    print()

    # ----------------------- Start server without blocking this coroutine -----------------------
    await server.serve_forever(background=True)
    previous_plc_values = None


    # ----------------------- Main loop -----------------------
    # ---------------------------------------------------------

    while True:

        # ----------------------- Current UTC timestamp from PC -----------------------
        PC_Utc_DateTime = datetime.now(timezone.utc)

        pc_datetime = [
            PC_Utc_DateTime.year,
            PC_Utc_DateTime.month,
            PC_Utc_DateTime.isoweekday(),
            PC_Utc_DateTime.day,
            PC_Utc_DateTime.hour,
            PC_Utc_DateTime.minute,
            PC_Utc_DateTime.second,
            PC_Utc_DateTime.microsecond // 1000
        ]
        
        # ----------------------- Put UTC values into HR200 to HR207 registers -----------------------
        await server.async_setValues(
            device_id=DEVICE_ID,
            func_code=3,
            address=PC_DateTime_reg_group,
            values=pc_datetime
        )

        # Read HR100 to HR108 from local data address
        # ------------------------------------------
        # The PLC writes these registers using FC16

        PLC_Ntp_DateTime = await server.async_getValues(
            device_id=DEVICE_ID,
            func_code=3,
            address=Ntp_reg_group,
            count=Ntp_reg_Nb
        )

       # ----------------------- Decode PLC received DateTime data -----------------------
        if len(PLC_Ntp_DateTime) == Ntp_reg_Nb:
        
            Ntp_DateTime_year        = PLC_Ntp_DateTime[0]
            Ntp_DateTime_month       = PLC_Ntp_DateTime[1]
            Ntp_DateTime_weekday     = PLC_Ntp_DateTime[2]
            Ntp_DateTime_day         = PLC_Ntp_DateTime[3]
            Ntp_DateTime_hour        = PLC_Ntp_DateTime[4]
            Ntp_DateTime_minute      = PLC_Ntp_DateTime[5]
            Ntp_DateTime_second      = PLC_Ntp_DateTime[6]
            Ntp_DateTime_millisecond = PLC_Ntp_DateTime[7]
            Ntp_sync_status          = PLC_Ntp_DateTime[8]

        # ----------------------- Print valus only when they change -----------------------
        if PLC_Ntp_DateTime != previous_plc_values:

            print(
                f"PLC UTC: "
                f"{Ntp_DateTime_year:04d}-{Ntp_DateTime_month:02d}-{Ntp_DateTime_day:02d} "
                f"{Ntp_DateTime_hour:02d}:{Ntp_DateTime_minute:02d}:{Ntp_DateTime_second:02d}."
                f"{Ntp_DateTime_millisecond:03d}"
            )

            print(f"PLC weekday: {Ntp_DateTime_weekday}")
            print(f"NTP request: {Ntp_sync_status}")

            if Ntp_sync_status == Request_PC_TimeStamp:

                print("PLC requests UTC time from PC")
                print(
                    f"PC UTC prepared: "
                    f"{PC_Utc_DateTime.year:04d}-"
                    f"{PC_Utc_DateTime.month:02d}-"
                    f"{PC_Utc_DateTime.day:02d} "
                    f"{PC_Utc_DateTime.hour:02d}:"
                    f"{PC_Utc_DateTime.minute:02d}:"
                    f"{PC_Utc_DateTime.second:02d}."
                    f"{PC_Utc_DateTime.microsecond // 1000:03d}"
                )

            print()

            previous_plc_values = PLC_Ntp_DateTime.copy()

        # ----------------------- Put small delay so python does not use 100% CPU
        await asyncio.sleep(0.1)

# ----------------------- Start main -----------------------
if __name__ == "__main__":
    asyncio.run(main())