PACKAGES_DIR	= venv/lib/python2.7/site-packages/
PIP				= venv/bin/pip
VIRTUALENV		= virtualenv
ROOT_DIR		= $(shell pwd)
ZIP				= lambda.zip
CODE			= hmbot.py
FUNCTION		= hmbot

.PHONY: all
all: .added-to-zip

.added-to-zip: $(ZIP) $(CODE)
	zip -r $(ZIP) $(CODE) && touch .added-to-zip

$(ZIP): .venv-built 
	cd $(PACKAGES_DIR) && zip -r $(ROOT_DIR)/$@ .

$(PACKAGES_DIR)/$(ZIP): $(ZIP)
	cp $(ZIP) $(PACKAGES_DIR)

.venv-built:
	$(VIRTUALENV) -p python2.7 venv
	$(PIP) install -r requirements.txt
	touch .venv-built

.PHONY: clean
clean:
	rm -rf venv .venv-built .added-to-zip

.PHONY: upload
upload: all
	aws lambda update-function-code --function-name $(FUNCTION) --zip-file fileb://$(ROOT_DIR)/$(ZIP) --publish --profile hm
