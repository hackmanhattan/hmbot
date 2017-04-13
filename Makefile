PYTHON = python3.6

.PHONY: venv
venv: .venv-built

.venv-built:
	venv/bin/pip3 install -r requirements.txt && touch .venv-built

docker-rm: docker-stop
	docker rm hmbot

docker-run: docker-build
	docker run -d -e SQLITE_DB=$(SQLITE_DB) -e SLACK_TOKEN=$(SLACK_TOKEN) -e VERIFICATION_TOKEN=$(VERIFICATION_TOKEN) -p 127.0.0.1:2081:8080 --name hmbot hmbot

docker-stop:
	docker stop hmbot

docker-build:
	docker build -t hmbot .

docker-from-scratch: docker-rm docker-run

.PHONY: clean
clean:
	rm -rf venv .venv-built
