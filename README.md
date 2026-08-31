# Developing-time-synchronization-in-ABB-AC500-PLC-from-Network-Time-Protocol-and-PC-using-Python
As industrial design in synchronizing a programmable - logic - controller (PLC) using Network-Time-Protocol, a weakness arises when communication to NTP is lost and the client in other side expects that configured scheduler will perform without worries, a solution to this is - use two sources for time synchronization and rise NTP server alarm.

I developed a Modbus TCP communication between ABB PLC and PC and implemented NTP time synchronization by using libraries:
  1) SysTimeRtc = SysTimeRtc, 3.5.21.30 (System)
  2) AC500_ModbusTcp = ModbusTcp, 1.1.10.3 (ABB)
  3) AC500_Pm = Pm, 1.2.11.4 (ABB)
 
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
If NTP synchronization fails 5 times, alarm has been rised, for STRING retrieved DateAndTime from PC is used instead.
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
