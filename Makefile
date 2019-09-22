VENV_NAME?=venv
VENV_ACTIVATE=. $(VENV_NAME)/bin/activate

venv: $(VENV_NAME)/bin/activate
$(VENV_NAME)/bin/activate: requirements.txt
	test -d $(VENV_NAME) || virtualenv -p python $(VENV_NAME)
	$(VENV_NAME)/bin/pip install -Ur requirements.txt

test_venv: venv
	$(VENV_NAME)/bin/pip install -Ur requirements-dev.txt

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
	rm -rf venv
	rm -rf distro

TIMESTAMP:=$(shell date +%FT%T%Z)
distro:
	pip install -t ./distro -U -r requirements.txt
	cd distro && zip -r9 ../stream_notifier_${TIMESTAMP}.zip .
	zip -g ./stream_notifier_${TIMESTAMP}.zip stream_notifier.py

