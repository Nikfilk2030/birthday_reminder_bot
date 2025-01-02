#!/bin/bash

# file formatting
black .

# docker running
sudo docker compose down
sudo docker compose up --build
