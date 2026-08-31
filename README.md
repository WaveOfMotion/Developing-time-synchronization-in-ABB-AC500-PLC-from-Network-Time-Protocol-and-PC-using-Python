# Developing-time-synchronization-in-ABB-AC500-PLC-from-Network-Time-Protocol-and-PC-using-Python
As industrial design in synchronizing a programmable - logic - controller (PLC) using Network-Time-Protocol, a weakness arises when communication to NTP is lost and the client in other side expects that configured scheduler will perform without worries, a solution to this is - use two sources for time synchronization and rise NTP server alarm.

In my Python script, I use pymodbus library, and for installation on Windows, you need to open your command-line-prompt and type:
```
pip install pymodbus
```
, and the documentation is available in:
```iecst
https://pymodbus.readthedocs.io/en/latest/
```

Apart from everything else, I developed a Modbus TCP communication between ABB PLC and PC and implemented NTP time synchronization by using libraries:
  1) SysTimeRtc = SysTimeRtc, 3.5.21.30 (System)
  2) AC500_ModbusTcp = ModbusTcp, 1.1.10.3 (ABB)
  3) AC500_Pm = Pm, 1.2.11.4 (ABB)

## PLC-programing
In my application, I call SysTimeRtc function and conversion to date:
```iecst
eHighResConvertResult := SysTimeRtc.SysTimeRtcConvertHighResToDate(
							     pTimestamp := UtcTimestamp,
								 pDate      := UtcDateTime
);
```
, and I also call RealTimeClock, but it is used only to check if no error is being returned in hardware level:
```iecst
RealTimeClock(
	Enable  := TRUE,
	Set     := FALSE,
	ErrorID => Pm_ErrorID
);
```
I create a struct and attach the returned pointer "UtcDateTime" data to a predefined struct:
```iecst
IF xHighResRtcValid THEN
	NTP_DateAndTIme.YearAct 	  := UtcDateTime.wYear;
	NTP_DateAndTIme.MonAct  	  := UINT_TO_BYTE(UtcDateTime.wMonth);
	NTP_DateAndTIme.DayAct  	  := UINT_TO_BYTE(UtcDateTime.wDay);
	NTP_DateAndTIme.WDayAct 	  := UINT_TO_BYTE(UtcDateTime.wDayOfWeek);
	NTP_DateAndTIme.HourAct 	  := UINT_TO_BYTE(UtcDateTime.wHour);
	NTP_DateAndTIme.MinAct  	  := UINT_TO_BYTE(UtcDateTime.wMinute);
	NTP_DateAndTIme.SecAct  	  := UINT_TO_BYTE(UtcDateTime.wSecond);
	NTP_DateAndTIme.MilisecondAct := UtcDateTime.wMilliseconds;
END_IF
```
Then validity checks are taken in account and no errors pop up, this block returns the final judgement call:
```iecst
NTP_DateAndTIme.xTimeValid := 
	NOT RealTimeClock.Error
	AND xRtcValuesInRange
	AND xHighResRtcValid
	
	AND (Pm_ErrorID = AC500_Pm.ERROR_ID.NO_ERROR)
	AND (Ntp_ErrorID = AC500_Pm.ERROR_ID.NO_ERROR)
	
	AND xNtpSynchronized
	AND xNtpServerReachable
	AND xEth1_LinkUp;
```
I also add another validity check, if synchronization with NTP fails more than 5 times then I trigger an alarm:
```iecst
IF fbNtpPollTimer.Q AND NOT xNtpSynchronized THEN
	NTP_sync_CommErr := NTP_sync_CommErr + 1;
END_IF
IF (NTP_sync_CommErr >= 5) THEN (* --> Time sync failed at least 5 times *)
	NTP_sync_Alarm := TRUE;
ELSIF xNtpSynchronized THEN
	NTP_sync_Alarm := FALSE;
	NTP_sync_CommErr := 0;
END_IF
```
In ModbusTCP program, I call a function:
```iecst
sDateTime := UINT_TO_STRING(YearAct);

sDateTime := CONCAT(sDateTime, '-');
sDateTime := CONCAT(sDateTime, BYTE_TO_STRING(MonAct));

sDateTime := CONCAT(sDateTime, '-');
sDateTime := CONCAT(sDateTime, BYTE_TO_STRING(DayAct));

sDateTime := CONCAT(sDateTime, ' ');
sDateTime := CONCAT(sDateTime, BYTE_TO_STRING(HourAct));

sDateTime := CONCAT(sDateTime, ':');
sDateTime := CONCAT(sDateTime, BYTE_TO_STRING(MinAct));

sDateTime := CONCAT(sDateTime, ':');
sDateTime := CONCAT(sDateTime, BYTE_TO_STRING(Secact));

sDateTime := CONCAT(sDateTime, ':');
sDateTime := CONCAT(sDateTime, UINT_TO_STRING(MilisecondAct));

DateAndTime_FUN := sDateTime;
```
, that constructs a timestamp type STRING:
```iecst
'2026-8-31 11:11:42:656'
```
### Important
If NTP synchronization fails 5 times, alarm has been rised, for the STRING - retrieved DateAndTime from PC is then used instead.

Apart from everything else, I have two ModbusTCP requests - one sends time to my PC through Wi-fi, other recieves Timestamp from my PC.
```iecst
TARGET_IP_DWORD   := IP_ADR_STRING_TO_DWORD(TARGET_IP);

ModTcp.Execute := TRUE;
ModTcp.Eth     := AC500_Ethernet.ETH.ETH1;
ModTcp.IPAdr   := TARGET_IP_DWORD;
ModTcp.ParallelProcessing := FALSE;
ModTcp.UnitID  := 1;

ModTcp.Fct     := 16;
ModTcp.Addr    := 100;
ModTcp.Nb      := 9;
ModTcp.Data    := ADR(NTP_synced_data);
```
```iecst
TARGET_IP_DWORD   := IP_ADR_STRING_TO_DWORD(TARGET_IP);

ModTcp.Execute := TRUE;
ModTcp.Eth     := AC500_Ethernet.ETH.ETH1;
ModTcp.IPAdr   := TARGET_IP_DWORD;
ModTcp.ParallelProcessing := FALSE;
ModTcp.UnitID  := 1;

ModTcp.Fct     := 3;
ModTcp.Addr    := 200;
ModTcp.Nb      := 8;
ModTcp.Data    := ADR(PC_recv_DT);
```
## Python-programing
In Python I first import libraries:
```
import asyncio
from datetime import datetime, timezone

from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice
```
Then you must define your Modbus port which is 502, and your IP address, where I use my Wi-fi adapter, since I am on the same network as my PLC:
```
PC_IP = "192.168.1.207"
MODBUS_PORT = 502
DEVICE_ID = 1
```
You can check your Wi-fi adapter IP address by opening command-line-prompt, and entering: ```iecst ipconfig ```

The Modbus comunication itself is implemented in a way, that I send 8 registers to my PC, where the extra 9th register returns a non-zero value if PLC can't synchronize with NTP more than 5 times. And the same way, PC sends 8 registers to my PLC, where in this project, my PC acts as the backup time synchronzation source.

Later on, I call asynchronous function to use function 'await', and allow background processing by configuring my Modbus Server as non-blocking:
```iecst
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

# ----------------------- Start server without blocking this coroutine -----------------------
    await server.serve_forever(background=True)
    previous_plc_values = None
```
The important part is that you see, that I construct DateAndTime data outside an statement IF function like:
```
if Ntp_sync_status == Request_PC_TimeStamp:
...
```
, because I want this:
```
PC_Utc_DateTime = datetime.now(timezone.utc)
```
, to be created while connection is active. If I would put this function call inside an 'if' statement, it would be created only when the 'if' statement is satisified. So PLC always reads and gets DateAndTime from PC, it just decides when to use it as main source.

Important here, is now that PC acts as Modbus Server, it just needs to allocate data memory where to store its DateAndTime, so I store it:
```iecst
await server.async_setValues(
            device_id=DEVICE_ID,
            func_code=3,
            address=PC_DateTime_reg_group,
            values=pc_datetime
        )
```
As you see, for storing values I don't need to specify - 'count' , only address. In other words, for:
```iecst
server.async_getValues
```
, you must specify, but for:
```iecst
await server.async_setValues
```
, you don't.

For 'await server.async_setValues' you specify your array:
```iecst
values=pc_datetime
```
, where if you look a bit higher, I create an array, and the number of elements of that array is interpreted as number of elements.

Later on, I am adding an 'optional', that if you want to see values being printed by function 'print' , you would say: values has changed ?: print. So I define my idea as:
```iecst
if PLC_Ntp_DateTime != previous_plc_values:

... print values

previous_plc_values = PLC_Ntp_DateTime.copy()
```
This prints everytime, if values has changed.

Then in the end, you would see the last line as:
```iecst
await asyncio.sleep(0.1)
```
, where basically this decreases consumed RAM by the Python running, putting it asleep every 100 ms everytime when new values from the PLC are being received.

The last function:
```
if __name__ == "__main__":
    asyncio.run(main())
```
, can be interpreted as following:

When you start your script which includes function main(), a function:
```iecst __name__ ``` 
, at that moment is created, and its value is: 
```iecst "__main__" ``` 
Since I am running asynchronous function defined as main(), I must enter the last line as showed before.

# Conclusion
After developing Network-Time-Sinchronization from two sources using Modbus TCP, I constructed a STRING of Timestamp, which in further devlepment could be sent through IEC 60870-5-101 communication protocol or TCP/IP communication. Modbus TCP was used only as a industrial communication example.

