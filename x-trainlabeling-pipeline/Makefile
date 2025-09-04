VENV?=.venv
PYTHON?=$(VENV)/Scripts/python.exe
PIP?=$(VENV)/Scripts/pip.exe

.PHONY: venv install dev dag test lint format train

venv:
	python -m venv $(VENV)

install: venv
	$(PIP) install -r requirements.txt

dev: install
	$(PIP) install -e .[dev]

lint:
	$(PYTHON) -m ruff check src

format:
	$(PYTHON) -m ruff check --fix src
	$(PYTHON) -m ruff format src

dag:
	$(PYTHON) airflow/dags/x_trainlabeling_dag.py --print-structure

train:
	$(PYTHON) src/train/train_yolov8_seg.py --config configs/project.yaml

