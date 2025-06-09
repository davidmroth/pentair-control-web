"""
Resources:
- https://www.wolfteck.com/2019/02/05/pentair_pump_rs-485_api/#0x07-pump-status
- https://www.pentair.com/content/dam/extranet/nam/pentair-pool/pool-manuals/intellipro-vs-svrs/IntelliFlo_VSSVRS_IntelliPro_VSSVRS_Owners_Manual_English.pdf
"""

import os
import uvicorn
import logging
import pypentair

from loguru import logger
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pypentair.pump import SETTING, WEEKDAYS, PUMP_MODES
from typing import Optional, List


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure logger
logger.add("pool_pump.log", rotation="1 MB", level="DEBUG")
logging.getLogger("uvicorn.access").disabled = True

# Pump ID and serial port
PUMP_ID = 0x60
SERIAL_PORT = "/dev/ttyUSB0"
os.environ["PYPENTAIR_PORT"] = SERIAL_PORT


# Pydantic models
class StatusResponse(BaseModel):
    state: bool
    speed: int
    watts: int
    mode: str
    time: List[int]  # [hours, minutes]


class PumpControl(BaseModel):
    state: Optional[bool] = None
    speed: Optional[int] = None
    ramp: Optional[int] = None
    celsius: Optional[bool] = None
    fahrenheit: Optional[bool] = None
    contrast: Optional[int] = None
    address: Optional[int] = None
    id: Optional[int] = None
    ampm: Optional[bool] = None
    max_rpm: Optional[int] = None
    min_rpm: Optional[int] = None
    quick_rpm: Optional[int] = None
    quick_timer: Optional[List[int]] = None
    prime_enable: Optional[bool] = None
    prime_max_time: Optional[int] = None
    prime_sensitivity: Optional[int] = None
    prime_delay: Optional[int] = None
    antifreeze_enable: Optional[bool] = None
    antifreeze_rpm: Optional[int] = None
    antifreeze_temp: Optional[int] = None
    svrs_restart_enable: Optional[bool] = None
    svrs_restart_timer: Optional[int] = None
    time_out_timer: Optional[List[int]] = None
    running_program: Optional[int] = None
    selected_program: Optional[int] = None

class DatetimeControl(BaseModel):
    hour: Optional[int] = None
    minute: Optional[int] = None
    dow: Optional[str] = None  # e.g., "SUNDAY"
    dom: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None
    dst: Optional[bool] = None
    auto_dst: Optional[bool] = None
    sync_system: Optional[bool] = False

class ProgramControl(BaseModel):
    program_id: int
    rpm: Optional[int] = None
    mode: Optional[str] = None
    schedule_start: Optional[List[int]] = None
    schedule_end: Optional[List[int]] = None
    egg_timer: Optional[List[int]] = None


class RunRequest(BaseModel):
    state: bool  # True to start, False to stop the pump

@app.get("/", response_class=HTMLResponse)
async def get_root():
    logger.info("Root endpoint accessed")
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        logger.error("index.html not found in templates directory")
        raise HTTPException(status_code=500, detail="Template file not found")
    except Exception as e:
        logger.error(f"Error reading index.html: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status() -> StatusResponse:
    try:
        pump = pypentair.Pump(id=1)
        status = pump.status
        #logger.debug(f"Raw status: {status}")
        response = StatusResponse(
            state=status.get("run", 0) == 0x0A,  # 0x0A means running
            speed=status.get("rpm", 0),
            watts=status.get("watts", 0),
            mode={v: k for k, v in PUMP_MODES.items()}.get(status.get("mode", 0), "UNKNOWN"),
            time=[status.get("time", [0, 0])[0], status.get("time", [0, 0])[1]],
        )
        #logger.info(f"Pump status retrieved: {response}")
        return response
    except Exception as e:
        logger.error(f"Error retrieving pump status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config")
async def get_config():
    try:
        pump = pypentair.Pump(id=1)
        programs = []
        for i in range(1, 5):  # Programs 1-4
            logger.debug(f"Retrieving program {i}")
            program = pump.program(i)
            programs.append(
                {
                    "program_id": i,
                    "rpm": program.rpm,
                    "mode": ["MANUAL", "EGG_TIMER", "SCHEDULE"][
                        program.mode
                    ],
                    "schedule_start": program.schedule_start,
                    "schedule_end": program.schedule_end,
                    "egg_timer": program.egg_timer,
                }
            )
        dt = pump.dt
        logger.debug(f"Pump datetime: {dt}")

        run = pump.run
        logger.debug(f"Pump run status: {run}")

        response = {
            "ramp": pump.ramp,
            "celsius": pump.celsius,
            "fahrenheit": pump.fahrenheit,
            "contrast": pump.contrast,
            "address": pump.address,
            "id": pump.id,
            "ampm": pump.ampm,
            "max_rpm": pump.max_rpm,
            "min_rpm": pump.min_rpm,
            "quick_rpm": pump.quick_rpm,
            "quick_timer": pump.quick_timer,
            "prime_enable": pump.prime_enable,
            "prime_max_time": pump.prime_max_time,
            "prime_sensitivity": pump.prime_sensitivity,
            "prime_delay": pump.prime_delay,
            "antifreeze_enable": pump.antifreeze_enable,
            "antifreeze_rpm": pump.antifreeze_rpm,
            "antifreeze_temp": pump.antifreeze_temp,
            "svrs_restart_enable": pump.svrs_restart_enable,
            "svrs_restart_timer": pump.svrs_restart_timer,
            "time_out_timer": pump.time_out_timer,
            "running_program": pump.get(SETTING["RUNNING_PROGRAM"]) // 8,
            # Implement later
            "datetime": {
                "hour": dt[0],
                "minute": dt[1],
                "dow": {v: k for k, v in WEEKDAYS.items()}.get(dt[2], "SUNDAY"),
                "dom": dt[3],
                "month": dt[4],
                "year": dt[5],
                "dst": dt[6],
            },
            "programs": programs,
        }
        logger.info(f"Config retrieved: {response}")
        return response
    except Exception as e:
        logger.error(f"Error retrieving config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run")
async def run_pump(control: RunRequest):
    try:
        pump = pypentair.Pump(id=1)
        pump.run = control.state
        logger.info(f"Pump {'started' if control.state else 'stopped'} (pump.run={pump.run})")
        return {"status": "success", "message": f"Pump {'started' if control.state else 'stopped'}"}
    except Exception as e:
        logger.error(f"Error changing pump status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
async def stop_pump():
    try:
        pump = pypentair.Pump(id=1)
        pump.stop
        logger.info("Pump stopped")
        return {"status": "success", "message": "Pump stopped"}
    except Exception as e:
        logger.error(f"Error stopping pump: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/control")
async def control_pump(control: PumpControl):
    try:
        pump = pypentair.Pump(id=1)

        if control.state is not None:
            pump.run = 0x0A if control.state else 0x04
            logger.info(f"Pump {'started' if control.state else 'stopped'}")

        if control.speed is not None:
            if 450 <= control.speed <= 3450:
                pump.trpm = control.speed
                logger.info(f"Pump speed set to {control.speed} RPM")
            else:
                logger.warning(f"Invalid speed requested: {control.speed}")
                raise HTTPException(
                    status_code=400, detail="Speed must be between 450 and 3450 RPM"
                )
        if control.ramp is not None:
            if 100 <= control.ramp <= 200:
                pump.ramp = control.ramp
                logger.info(f"Ramp set to {control.ramp}")
            else:
                logger.warning(f"Invalid ramp: {control.ramp}")
                raise HTTPException(
                    status_code=400, detail="Ramp must be between 100 and 200"
                )
        if control.celsius is not None:
            pump.celsius = control.celsius
            logger.info(f"Celsius set to {control.celsius}")
        if control.fahrenheit is not None:
            pump.fahrenheit = control.fahrenheit
            logger.info(f"Fahrenheit set to {control.fahrenheit}")
        if control.contrast is not None:
            if 1 <= control.contrast <= 3:
                pump.contrast = control.contrast
                logger.info(f"Contrast set to {control.contrast}")
            else:
                logger.warning(f"Invalid contrast: {control.contrast}")
                raise HTTPException(
                    status_code=400, detail="Contrast must be between 1 and 3"
                )
        if control.address is not None:
            if 96 <= control.address <= 97:
                pump.address = control.address
                logger.info(f"Address set to {control.address}")
            else:
                logger.warning(f"Invalid address: {control.address}")
                raise HTTPException(
                    status_code=400, detail="Address must be between 96 and 97"
                )
        if control.id is not None:
            if 1 <= control.id <= 2:
                pump.id = control.id
                logger.info(f"ID set to {control.id}")
            else:
                logger.warning(f"Invalid id: {control.id}")
                raise HTTPException(
                    status_code=400, detail="ID must be between 1 and 2"
                )
        if control.ampm is not None:
            pump.ampm = control.ampm
            logger.info(f"AM/PM set to {control.ampm}")
        if control.max_rpm is not None:
            if 3445 <= control.max_rpm <= 3450:
                pump.max_rpm = control.max_rpm
                logger.info(f"Max RPM set to {control.max_rpm}")
            else:
                logger.warning(f"Invalid max_rpm: {control.max_rpm}")
                raise HTTPException(
                    status_code=400, detail="Max RPM must be between 3445 and 3450"
                )
        if control.min_rpm is not None:
            if 1100 <= control.min_rpm <= 1105:
                pump.min_rpm = control.min_rpm
                logger.info(f"Min RPM set to {control.min_rpm}")
            else:
                logger.warning(f"Invalid min_rpm: {control.min_rpm}")
                raise HTTPException(
                    status_code=400, detail="Min RPM must be between 1100 and 1105"
                )
        if control.quick_rpm is not None:
            if 2000 <= control.quick_rpm <= 3000:
                pump.quick_rpm = control.quick_rpm
                logger.info(f"Quick RPM set to {control.quick_rpm}")
            else:
                logger.warning(f"Invalid quick_rpm: {control.quick_rpm}")
                raise HTTPException(
                    status_code=400, detail="Quick RPM must be between 2000 and 3000"
                )
        if control.quick_timer is not None:
            if 0 <= control.quick_timer[0] <= 9 and 0 <= control.quick_timer[1] <= 59:
                pump.quick_timer = control.quick_timer
                logger.info(f"Quick timer set to {control.quick_timer}")
            else:
                logger.warning(f"Invalid quick_timer: {control.quick_timer}")
                raise HTTPException(
                    status_code=400, detail="Quick timer hours 0-9, minutes 0-59"
                )
        if control.prime_enable is not None:
            pump.prime_enable = control.prime_enable
            logger.info(f"Prime enable set to {control.prime_enable}")
        if control.prime_max_time is not None:
            if 1 <= control.prime_max_time <= 30:
                pump.prime_max_time = control.prime_max_time
                logger.info(f"Prime max time set to {control.prime_max_time}")
            else:
                logger.warning(f"Invalid prime_max_time: {control.prime_max_time}")
                raise HTTPException(
                    status_code=400, detail="Prime max time must be between 1 and 30"
                )
        if control.prime_sensitivity is not None:
            if 1 <= control.prime_sensitivity <= 100:
                pump.prime_sensitivity = control.prime_sensitivity
                logger.info(f"Prime sensitivity set to {control.prime_sensitivity}")
            else:
                logger.warning(
                    f"Invalid prime_sensitivity: {control.prime_sensitivity}"
                )
                raise HTTPException(
                    status_code=400,
                    detail="Prime sensitivity must be between 1 and 100",
                )
        if control.prime_delay is not None:
            if 1 <= control.prime_delay <= 600:
                pump.prime_delay = control.prime_delay
                logger.info(f"Prime delay set to {control.prime_delay}")
            else:
                logger.warning(f"Invalid prime_delay: {control.prime_delay}")
                raise HTTPException(
                    status_code=400, detail="Prime delay must be between 1 and 600"
                )
        if control.antifreeze_enable is not None:
            pump.antifreeze_enable = control.antifreeze_enable
            logger.info(f"Antifreeze enable set to {control.antifreeze_enable}")
        if control.antifreeze_rpm is not None:
            if 1100 <= control.antifreeze_rpm <= 3000:
                pump.antifreeze_rpm = control.antifreeze_rpm
                logger.info(f"Antifreeze RPM set to {control.antifreeze_rpm}")
            else:
                logger.warning(f"Invalid antifreeze_rpm: {control.antifreeze_rpm}")
                raise HTTPException(
                    status_code=400,
                    detail="Antifreeze RPM must be between 1100 and 3000",
                )
        if control.antifreeze_temp is not None:
            if 40 <= control.antifreeze_temp <= 50:
                pump.antifreeze_temp = control.antifreeze_temp
                logger.info(f"Antifreeze temp set to {control.antifreeze_temp}")
            else:
                logger.warning(f"Invalid antifreeze_temp: {control.antifreeze_temp}")
                raise HTTPException(
                    status_code=400, detail="Antifreeze temp must be between 40 and 50"
                )
        if control.svrs_restart_enable is not None:
            pump.svrs_restart_enable = control.svrs_restart_enable
            logger.info(f"SVRS restart enable set to {control.svrs_restart_enable}")
        if control.svrs_restart_timer is not None:
            if 30 <= control.svrs_restart_timer <= 300:
                pump.svrs_restart_timer = control.svrs_restart_timer
                logger.info(f"SVRS restart timer set to {control.svrs_restart_timer}")
            else:
                logger.warning(
                    f"Invalid svrs_restart_timer: {control.svrs_restart_timer}"
                )
                raise HTTPException(
                    status_code=400,
                    detail="SVRS restart timer must be between 30 and 300",
                )
        if control.time_out_timer is not None:
            if (
                0 <= control.time_out_timer[0] <= 9
                and 0 <= control.time_out_timer[1] <= 59
            ):
                pump.time_out_timer = control.time_out_timer
                logger.info(f"Time out timer set to {control.time_out_timer}")
            else:
                logger.warning(f"Invalid time_out_timer: {control.time_out_timer}")
                raise HTTPException(
                    status_code=400, detail="Time out timer hours 0-9, minutes 0-59"
                )
        if control.running_program is not None:
            if 1 <= control.running_program <= 4:
                pump.set(
                    pypentair.SETTING["RUNNING_PROGRAM"], control.running_program * 8
                )
                logger.info(f"Running program set to {control.running_program}")
            else:
                logger.warning(f"Invalid running_program: {control.running_program}")
                raise HTTPException(
                    status_code=400, detail="Running program must be between 1 and 4"
                )
        if control.selected_program is not None:
            if 1 <= control.selected_program <= 8:
                pump.selected_program = control.selected_program
                logger.info(f"Selected program set to {control.selected_program}")
            else:
                logger.warning(f"Invalid selected_program: {control.selected_program}")
                raise HTTPException(
                    status_code=400, detail="Selected program must be between 1 and 4"
                )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error controlling pump: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/program")
async def control_program(control: ProgramControl):
    try:
        logger.debug(f"Received program control: {control.dict()}")
        if not 1 <= control.program_id <= 8:
            logger.warning(f"Invalid program_id: {control.program_id}")
            raise HTTPException(
                status_code=400, detail="Program ID must be between 1 and 8"
            )
        pump = pypentair.Pump(id=1)

        # Check if pump running (via mode). If so, respond with error
        logger.debug(f"Current pump mode: {pump.mode}")
        if pump.mode:
            logger.warning("Pump is currently running, cannot modify program")
            raise HTTPException(
                status_code=400, detail="Pump is currently running, cannot modify program"
            )

        program = pump.program(control.program_id)
        logger.debug(f"Program methods: {dir(program)}")

        if control.mode is not None:
            mode_map = {"MANUAL": 0, "EGG_TIMER": 1, "SCHEDULE": 2, "DISABLED": 3}
            if control.mode in mode_map:
                logger.debug(f"Setting program mode from {program.mode} to {control.mode} ({mode_map[control.mode]})")
                program.mode = mode_map[control.mode]
            else:
                logger.warning(f"Invalid program mode: {control.mode}")
                raise HTTPException(
                    status_code=400,
                    detail="Mode must be MANUAL, EGG_TIMER, SCHEDULE, or DISABLED",
                )
        if control.rpm is not None:
            if 450 <= control.rpm <= 3450:
                program.rpm = control.rpm
                logger.info(f"Program {control.program_id} RPM set to {control.rpm}")
            else:
                logger.warning(f"Invalid program RPM: {control.rpm}")
                raise HTTPException(
                    status_code=400, detail="Program RPM must be between 450 and 3450"
                )
        if control.schedule_start is not None:
            if (
                len(control.schedule_start) == 2
                and 0 <= control.schedule_start[0] <= 23
                and 0 <= control.schedule_start[1] <= 59
            ):
                program.schedule_start = control.schedule_start
                logger.info(
                    f"Program {control.program_id} schedule start set to {control.schedule_start}"
                )
            else:
                logger.warning(f"Invalid schedule_start: {control.schedule_start}")
                raise HTTPException(
                    status_code=400,
                    detail="Schedule start must have hours 0-23, minutes 0-59",
                )
        if control.schedule_end is not None:
            if (
                len(control.schedule_end) == 2
                and 0 <= control.schedule_end[0] <= 23
                and 0 <= control.schedule_end[1] <= 59
            ):
                program.schedule_end = control.schedule_end
                logger.info(
                    f"Program {control.program_id} schedule end set to {control.schedule_end}"
                )
            else:
                logger.warning(f"Invalid schedule_end: {control.schedule_end}")
                raise HTTPException(
                    status_code=400,
                    detail="Schedule end must have hours 0-23, minutes 0-59",
                )
        if control.egg_timer is not None:
            if (
                len(control.egg_timer) == 2
                and 0 <= control.egg_timer[0] <= 23
                and 0 <= control.egg_timer[1] <= 59
            ):
                program.egg_timer = control.egg_timer
                logger.info(
                    f"Program {control.program_id} egg timer set to {control.egg_timer}"
                )
            else:
                logger.warning(f"Invalid egg_timer: {control.egg_timer}")
                raise HTTPException(
                    status_code=400,
                    detail="Egg timer must have hours 0-23, minutes 0-59",
                )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error controlling program: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    logger.info("Starting FastAPI application")
    uvicorn.run(
        "main:app",
        port=8000,
        reload=True,
        reload_dirs=[".", "./templates", "./static"]
    )
