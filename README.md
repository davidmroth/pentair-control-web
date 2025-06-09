# Pentair IntelliFlo Web

A FastAPI web interface for controlling and monitoring Pentair IntelliFlo pool pumps via RS-485.

---

**Designed for Raspberry Pi with RS-485 Dongle**  
This project is intended to run on a Raspberry Pi using an RS-485 USB dongle to communicate with the pump.  
**Tested hardware:**  
[DSD TECH SH-U10 USB to RS485 Converter Adapter](https://www.amazon.com/dp/B081MB6PN2?ref=ppx_yo2ov_dt_b_fed_asin_title)

---

## Features

- View real-time pump status (on/off, speed, watts, mode, time)
- Configure pump settings (speed, ramp, temperature units, contrast, address, etc.)
- Start/stop pump and set speed
- Manage pump programs (manual, egg timer, schedule)
- Responsive web UI (served from `/templates/index.html`)
- REST API endpoints for integration

## Requirements

- Raspberry Pi (any model with USB)
- [DSD TECH SH-U10 USB to RS485 Converter Adapter](https://www.amazon.com/dp/B081MB6PN2?ref=ppx_yo2ov_dt_b_fed_asin_title)
- Python 3.8+
- [pypentair](https://github.com/davidnewhall/pypentair) (Python library for Pentair pumps)
- FastAPI
- Uvicorn
- loguru

## Installation

1. **Connect the RS-485 dongle** to your Raspberry Pi and wire it to the Pentair pump's RS-485 terminals.

2. **Clone the repository:**
    ```sh
    git clone https://github.com/yourusername/pentair-intelliflow-web.git
    cd pentair-intelliflow-web
    ```

3. **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

4. **Set up serial port permissions** (if needed):
    ```sh
    sudo usermod -a -G dialout $USER
    # Then log out and back in
    ```

## Usage

### Development

Run the FastAPI app with auto-reload:

```sh
python main.py
```

Or with Uvicorn CLI:

```sh
uvicorn main:app --reload --reload-dir templates --reload-dir static
```

The web interface will be available at [http://localhost:8000](http://localhost:8000).

### Production

Use a process manager (e.g., systemd, supervisor) and run without `--reload`.

## API Endpoints

- `GET /` - Web UI
- `GET /status` - Pump status (JSON)
- `GET /config` - Pump configuration (JSON)
- `POST /run` - Start/stop pump (`{"state": true|false}`)
- `POST /stop` - Stop pump
- `POST /control` - Set pump settings (see `PumpControl` model)
- `POST /program` - Set program settings (see `ProgramControl` model)

## Configuration

- Serial port is set via `SERIAL_PORT` in `main.py` (default: `/dev/ttyUSB0`)
- Pump ID is set via `PUMP_ID` in `main.py` (default: `1`)

## File Structure

```
pentair-intelliflow-web/
├── main.py
├── requirements.txt
├── templates/
│   └── index.html
├── static/
│   └── ... (static assets)
└── pool_pump.log
```

## Troubleshooting

- **422 Unprocessable Entity:**  
  Ensure your POST body matches the expected Pydantic model for each endpoint.
- **Serial port errors:**  
  Make sure your user has permission to access the serial port device.

## License

MIT License

---

**Credits:**  
- [pypentair](https://github.com/davidnewhall/pypentair)
- [FastAPI](https://fastapi.tiangolo.com/)
