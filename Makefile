.PHONY: install probe test eval evidence serve video docker-arm64 clean

PY := .venv/bin/python

install:
	uv venv --python 3.14 .venv
	uv pip install --python $(PY) -r requirements.txt

probe:
	$(PY) src/probe.py

test:
	$(PY) -m pytest -q

eval:
	$(PY) src/eval_harness.py --scenes 80

evidence:
	$(PY) src/make_evidence.py

video:
	bash docs/record_terminal.sh
	bash docs/make_video.sh

serve:
	$(PY) -m uvicorn src.service:app --host 0.0.0.0 --port 8080

docker-arm64:
	docker buildx build --platform linux/arm64 -f deploy/Dockerfile -t panelscan-agent:arm64 .

clean:
	rm -rf results/scenes .pytest_cache src/__pycache__ tests/__pycache__
