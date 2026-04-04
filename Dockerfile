FROM ghcr.io/benoitc/gunicorn:latest

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:80", "run:app"]