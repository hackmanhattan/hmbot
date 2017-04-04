PYTHON				= python3.6

.PHONY: venv
venv: .venv-built

.venv-built:
	venv/bin/pip3 install -r requirements.txt && touch .venv-built

.PHONY: clean
clean:
	rm -rf venv .venv-built
