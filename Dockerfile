FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy bot files
COPY bot.py .

CMD ["python", "bot.py"]
