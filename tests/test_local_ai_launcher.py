def local_values():
    return {
        "DEEPSEEK_BASE_URL": "http://127.0.0.1:11434/v1",
        "SPEECH_BASE_URL": "http://127.0.0.1:8766/v1",
        "DEEPSEEK_API_KEY": "local-fixture",
        "SILICONFLOW_API_KEY": "local-fixture",
        "LLM_MODEL": "local-model:test",
        "ASR_MODEL": "whisper-small",
        "TTS_MODEL": "windows-sapi",
        "TTS_VOICE": "Microsoft Huihui Desktop",
    }


def test_child_configuration_discards_inherited_model_overrides():
    from scripts.start_local_ai import child_environment

    values = local_values()
    inherited = {"deepseek_base_url": "https://external.invalid/v1",
                 "SPEECH_BASE_URL": "https://external.invalid/v1",
                 "LLM_MODEL": "alternate:cloud", "HTTP_PROXY": "http://proxy.invalid",
                 "NO_PROXY": "example.test", "INTERVIEW_WORKER_ENABLED": "false"}
    environment = child_environment(values, inherited)

    assert {key: environment[key] for key in values} == values
    assert "deepseek_base_url" not in environment
    assert "HTTP_PROXY" not in environment
    assert set(environment["NO_PROXY"].split(",")) == {"localhost", "127.0.0.1", "example.test"}
    assert environment["OLLAMA_NO_CLOUD"] == "1"
    assert environment["INTERVIEW_WORKER_ENABLED"] == "true"


def test_external_endpoint_is_rejected():
    import pytest
    from scripts.start_local_ai import child_environment

    with pytest.raises(ValueError, match="SPEECH_BASE_URL"):
        child_environment(dict(local_values(), SPEECH_BASE_URL="https://external.invalid/v1"), {})


def test_website_identity_and_models_must_match():
    from scripts.start_local_ai import child_environment, configured_services

    environment = child_environment(dict(local_values(), LLM_STRUCTURED_OUTPUT="true"), {})
    website = configured_services(environment, "ollama.exe")[-1]
    assert not website.matches({"status": "ok", "db": "ok"})
    compatible = {
        "status": "ok", "service": "task1-local-ai",
        "llm_model": "local-model:test", "asr_model": "whisper-small",
        "tts_model": "windows-sapi", "tts_voice": "Microsoft Huihui Desktop",
        "llm_structured_output": True,
    }
    assert website.matches(compatible)
    assert not website.matches(dict(compatible, llm_structured_output=False))


def test_monitor_recovers_only_owned_processes_and_stops_after_limit(monkeypatch):
    from types import SimpleNamespace
    from scripts.start_local_ai import HEALTH_FAILURE_LIMIT, RESTART_LIMIT, Service

    service = Service("Speech", 8766, "/healthz", lambda result: True, ["speech"])
    calls = []
    monkeypatch.setattr(service, "ready", lambda client: False)
    monkeypatch.setattr(service, "stop", lambda: calls.append("stop"))
    monkeypatch.setattr(service, "launch", lambda client, env: calls.append("launch"))
    for _ in range(HEALTH_FAILURE_LIMIT + 1):
        service.monitor(None, {})
    assert calls == []

    service.process = SimpleNamespace()
    for _ in range(HEALTH_FAILURE_LIMIT * (RESTART_LIMIT + 2)):
        service.monitor(None, {})
    assert calls == ["stop", "launch"] * RESTART_LIMIT


def test_launcher_drains_website_before_owned_dependencies(monkeypatch):
    from types import SimpleNamespace
    from scripts import start_local_ai

    events = []
    def fake_service(name):
        service = SimpleNamespace(name=name, port=0, process=None, ready=lambda client: False)
        def launch(client, environment):
            service.process = object()
            events.append("start " + name)
        service.launch = launch
        service.monitor = lambda client, environment: None
        service.stop = lambda: events.append("stop " + name)
        return service

    services = [fake_service(name) for name in ("model", "speech", "website")]
    monkeypatch.setattr(start_local_ai, "configured_services", lambda env, executable: services)
    monkeypatch.setattr(start_local_ai, "dotenv_values", lambda *args, **kwargs: local_values())
    monkeypatch.setattr(start_local_ai.shutil, "which", lambda name: "ollama")
    def interrupt(seconds):
        raise KeyboardInterrupt
    monkeypatch.setattr(start_local_ai.time, "sleep", interrupt)

    start_local_ai.start_services()

    assert events == [
        "start model", "start speech", "start website",
        "stop website", "stop speech", "stop model",
    ]


def test_launcher_monitors_when_all_services_are_adopted(monkeypatch):
    from types import SimpleNamespace
    from scripts import start_local_ai

    monitors = []
    service = SimpleNamespace(
        name="adopted", port=1, process=None,
        ready=lambda client: True,
        monitor=lambda client, env: monitors.append("poll"),
        stop=lambda: None,
    )
    monkeypatch.setattr(start_local_ai, "configured_services", lambda env, executable: [service])
    monkeypatch.setattr(start_local_ai, "dotenv_values", lambda *args, **kwargs: local_values())
    monkeypatch.setattr(start_local_ai.shutil, "which", lambda name: "ollama")
    def interrupt(seconds):
        raise KeyboardInterrupt
    monkeypatch.setattr(start_local_ai.time, "sleep", interrupt)

    start_local_ai.start_services()

    assert monitors == ["poll"]
