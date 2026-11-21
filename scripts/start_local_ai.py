"""Start and supervise this project's free local AI services on Windows."""

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from typing import Callable

from dotenv import dotenv_values
import httpx


ROOT = Path(__file__).resolve().parents[1]
TEXT_URL = "http://127.0.0.1:11434/v1"
SPEECH_URL = "http://127.0.0.1:8766/v1"
LOCAL_SETTINGS = {
    "DEEPSEEK_BASE_URL", "DEEPSEEK_API_KEY", "LLM_MODEL", "LLM_STRUCTURED_OUTPUT",
    "LLM_TIMEOUT_SECONDS", "LLM_MAX_RETRIES", "SPEECH_BASE_URL", "SILICONFLOW_API_KEY",
    "ASR_MODEL", "TTS_MODEL", "TTS_VOICE", "SPEECH_TIMEOUT_SECONDS", "SPEECH_MAX_RETRIES",
    "INTERVIEW_WORKER_ENABLED", "RESUME_EXPORT_WORKER_ENABLED", "NO_PROXY",
}
BLOCKED_INHERITED = LOCAL_SETTINGS | {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "OLLAMA_HOST", "OLLAMA_NO_CLOUD"}
START_TIMEOUT = 90
WEBSITE_DRAIN_TIMEOUT = 360
DEPENDENCY_STOP_TIMEOUT = 15
HEALTH_FAILURE_LIMIT = 3
RESTART_LIMIT = 2


def child_environment(local, inherited):
    for key, expected in (("DEEPSEEK_BASE_URL", TEXT_URL), ("SPEECH_BASE_URL", SPEECH_URL)):
        if local.get(key) != expected:
            raise ValueError(f"{key} must be {expected}")
    for key in ("DEEPSEEK_API_KEY", "SILICONFLOW_API_KEY", "LLM_MODEL", "ASR_MODEL", "TTS_MODEL", "TTS_VOICE"):
        if not local.get(key):
            raise ValueError(f"Missing local setting {key}")
    if local["LLM_MODEL"].lower().endswith((":cloud", "-cloud")):
        raise ValueError("LLM_MODEL must name a downloaded local Ollama model")

    environment = {key: value for key, value in inherited.items() if key.upper() not in BLOCKED_INHERITED}
    environment.update({key: local[key] for key in LOCAL_SETTINGS if local.get(key) is not None})
    configured_bypass = environment.get("NO_PROXY") or next(
        (value for key, value in inherited.items() if key.upper() == "NO_PROXY"), ""
    )
    bypass_hosts = [host.strip() for host in configured_bypass.split(",") if host.strip()]
    environment.update(
        NO_PROXY=",".join(dict.fromkeys([*bypass_hosts, "localhost", "127.0.0.1"])),
        OLLAMA_HOST="127.0.0.1:11434", OLLAMA_NO_CLOUD="1",
        INTERVIEW_WORKER_ENABLED="true", RESUME_EXPORT_WORKER_ENABLED="true",
    )
    return environment


@dataclass
class Service:
    name: str
    port: int
    health_path: str
    matches: Callable[[dict], bool]
    command: list[str]
    drain_timeout: int = DEPENDENCY_STOP_TIMEOUT
    process: subprocess.Popen | None = None
    failures: int = 0
    restarts: int = 0

    def ready(self, client):
        try:
            response = client.get(f"http://127.0.0.1:{self.port}{self.health_path}")
            return response.is_success and self.matches(response.json())
        except (httpx.HTTPError, ValueError, TypeError, AttributeError, KeyError):
            return False

    def launch(self, client, environment):
        # Never start a second process against a port with an incompatible owner.
        with socket.socket() as connection:
            connection.settimeout(1)
            if connection.connect_ex(("127.0.0.1", self.port)) == 0:
                raise RuntimeError(f"{self.name}: port {self.port} is already occupied by an incompatible process")
        self.process = subprocess.Popen(
            self.command, cwd=ROOT, env=environment,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
        deadline = time.monotonic() + START_TIMEOUT
        while not self.ready(client):
            if self.process.poll() is not None:
                raise RuntimeError(f"{self.name} exited with code {self.process.returncode}")
            if time.monotonic() >= deadline:
                raise RuntimeError(f"{self.name} did not become ready within {START_TIMEOUT} seconds")
            time.sleep(0.5)
        print(f"{self.name} ready on {self.port}", flush=True)

    def stop(self):
        process = self.process
        if process is None or process.poll() is not None:
            return
        print(f"Stopping {self.name}; allowing up to {self.drain_timeout} seconds", flush=True)
        try:
            process.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGTERM)
            process.wait(timeout=self.drain_timeout)
        except ProcessLookupError:
            return
        except subprocess.TimeoutExpired:
            print(f"{self.name} did not stop in time; forcing shutdown", file=sys.stderr, flush=True)
            process.kill()
            process.wait(timeout=DEPENDENCY_STOP_TIMEOUT)

    def monitor(self, client, environment):
        if self.ready(client):
            if self.failures >= HEALTH_FAILURE_LIMIT:
                print(f"{self.name} recovered", flush=True)
            self.failures = 0
            return
        self.failures += 1
        if self.failures == HEALTH_FAILURE_LIMIT:
            print(f"{self.name} is unavailable", file=sys.stderr, flush=True)
        # Adopted processes belong to their original supervisor.
        if self.process is None or self.failures < HEALTH_FAILURE_LIMIT or self.restarts >= RESTART_LIMIT:
            return
        self.restarts += 1
        print(f"Restarting {self.name} ({self.restarts}/{RESTART_LIMIT})", flush=True)
        try:
            self.stop()
            self.launch(client, environment)
            self.failures = 0
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            print(f"{self.name} restart failed: {error}", file=sys.stderr, flush=True)


def configured_services(environment, ollama):
    def local_model(data):
        return any(
            item["name"] == environment["LLM_MODEL"] and item["size"] > 0
            and not (item.get("remote_model") or item.get("remote_host"))
            for item in data["models"]
        )

    expected_website = {
        "status": "ok", "service": "task1-local-ai",
        **{key.lower(): environment[key] for key in ("LLM_MODEL", "ASR_MODEL", "TTS_MODEL", "TTS_VOICE")},
        "llm_structured_output": environment.get("LLM_STRUCTURED_OUTPUT", "").lower() in
        {"1", "true", "yes", "on", "y", "t"},
    }
    python = [sys.executable, "-B", "-m", "scripts.start_local_ai"]
    return [
        Service("Ollama", 11434, "/api/tags", local_model, [ollama, "serve"]),
        Service("Local speech", 8766, "/healthz", lambda data: data == {
            "status": "ok", "service": "task1-local-speech",
        }, [*python, "--serve", "speech"]),
        Service("Website", 8000, "/healthz/local-ai", lambda data: data == expected_website,
                [*python, "--serve", "website"], drain_timeout=WEBSITE_DRAIN_TIMEOUT),
    ]


def start_services():
    environment = child_environment(dotenv_values(ROOT / ".env", interpolate=False), os.environ)
    ollama = shutil.which("ollama")
    if ollama is None:
        raise RuntimeError("Ollama executable was not found")
    services = configured_services(environment, ollama)
    try:
        with httpx.Client(trust_env=False, timeout=2.0) as client:
            for service in services:
                if service.ready(client):
                    print(f"{service.name} already ready on {service.port}", flush=True)
                else:
                    service.launch(client, environment)

            print("Local project: http://127.0.0.1:8000/", flush=True)
            while True:
                for service in services:
                    service.monitor(client, environment)
                time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        for service in reversed(services):
            service.stop()


def serve(role):
    import uvicorn

    module, port = {"website": ("app.main:app", 8000), "speech": ("scripts.local_speech:app", 8766)}[role]
    server = uvicorn.Server(uvicorn.Config(module, host="127.0.0.1", port=port, workers=1, proxy_headers=False))
    if os.name == "nt":
        signal.signal(signal.SIGBREAK, server.handle_exit)
    server.run()


if __name__ == "__main__":
    try:
        if sys.argv[1:2] == ["--serve"] and len(sys.argv) == 3:
            serve(sys.argv[2])
        else:
            start_services()
    except (RuntimeError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        sys.exit(str(error))
