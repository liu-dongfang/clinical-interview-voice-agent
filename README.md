# clinical-interview-voice-agent

An interruption-aware voice agent for structured clinical interviewing, designed as a public showcase of reusable speech-agent infrastructure.

![Live interview interface](assets/readme/live-interview.png)

This repository highlights:
- Voice interview UX with a downstream app shell for registration and live interviewing
- Swappable STT / LLM / TTS / VAD / playback backends behind one orchestrator
- Interruption-aware control flow that can stop playback when new user speech is detected

**Demo:** [Watch 55s legacy mobile demo](docs/demo/voice-mobile-demo-55s.mp4) · [Read architecture notes](docs/architecture.md) · [Open live interface screenshot](assets/readme/live-interview.png)

## Overview

`clinical-interview-voice-agent` is the public-facing engineering subset of a larger research prototype for structured clinical interviewing. This repository focuses on the reusable speech stack: audio input, VAD-based interruption handling, ASR / LLM / TTS backend abstraction, dialogue orchestration, and a thin service layer for UI integration.

The linked demo is a lightweight legacy mobile walkthrough. The screenshots below represent the cleaner app shell used to present the same backend capabilities as a product-facing showcase.

## Interface

| Registration | Live interview |
| --- | --- |
| ![Registration screen](assets/readme/registration.png) | ![Live interview screen](assets/readme/live-interview.png) |

- The registration surface shows how user intake and configuration can be wrapped around the voice backend.
- The live interview view demonstrates a more inspectable product layer than raw logs or terminal output.
- Together they frame the system as reusable AI application infrastructure, not just a backend demo.

## Speech Flow

![Voice flow](assets/readme/voice-flow.png)

At a high level:
1. Audio enters through a recorder or browser bridge.
2. VAD decides whether speech is active and whether playback should be interrupted.
3. ASR converts finalized user audio into text for the orchestrator.
4. [`bailing/voice_agent.py`](bailing/voice_agent.py) maintains dialogue state and streams requests through the selected LLM backend.
5. Output text is segmented, synthesized incrementally, and sent to the selected playback backend.

## What This Repository Demonstrates

- Interruption-aware dialogue control instead of rigid turn-taking
- Clear backend boundaries across recorder, VAD, ASR, LLM, TTS, and playback
- A small service bridge in [`server/server.py`](server/server.py) for timeline inspection and UI integration
- Config-driven backend swapping through [`config/config.yaml`](config/config.yaml)

## What I Built

- Reframed the original research codebase into a smaller public showcase centered on the reusable voice engine
- Preserved interruption handling as a first-class system behavior rather than a demo-only feature
- Reworked the main execution path around a cleaner orchestrator in [`bailing/voice_agent.py`](bailing/voice_agent.py)
- Packaged the backend with screenshots, docs, and a minimal monitor so reviewers can understand both system design and product surface

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py --config config/config.yaml --no-speak
```

Notes:
- The default config is safe for inspection and uses `DummyLLM` plus `NoopPlayer`.
- Switch `selected_module.LLM` in [config/config.yaml](config/config.yaml) to `OpenAIChatLLM` or `OllamaLLM` if you want a different backend.
- Remove `--no-speak` and choose an active player backend when you want to test playback.

## Start Here

- [docs/architecture.md](docs/architecture.md)
- [bailing/voice_agent.py](bailing/voice_agent.py)
- [config/config.yaml](config/config.yaml)
- [server/server.py](server/server.py)
- [examples/domain_demo.md](examples/domain_demo.md)

## Limitations

- This is still an engineering prototype, not a production-ready realtime speech stack.
- Interruption quality depends on VAD thresholds, audio device behavior, and backend latency.
- The repository intentionally excludes large model weights, internal prompts, logs, certificates, and unpublished research materials.
