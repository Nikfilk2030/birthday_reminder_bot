#!/bin/bash

# file formatting
black .
isort .
flake8 .

# docker running
sudo docker compose down
sudo docker compose up --build
