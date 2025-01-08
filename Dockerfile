FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN python -m unittest discover -s . -p "test*.py"

EXPOSE 8000

CMD ["python", "bot.py"]
