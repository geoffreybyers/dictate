"""
Sidecar entry point: parse --config, set CONFIG_PATH, run FastAPI on 127.0.0.1:39821.
"""
import argparse
import uvicorn

from server import app, CONFIG_PATH
import server as server_module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to settings.json")
    args = parser.parse_args()
    server_module.CONFIG_PATH = args.config
    uvicorn.run(app, host="127.0.0.1", port=39821, log_level="info")


if __name__ == "__main__":
    main()
