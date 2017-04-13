PYTHON = python3.6

.PHONY: venv
venv: .venv-built

.venv-built:
	venv/bin/pip3 install -r requirements.txt && touch .venv-built

docker-build:
	docker build -t hmbot .

.PHONY: clean
clean:
	rm -rf venv .venv-built
