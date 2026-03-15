FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create uploads directory
RUN mkdir -p uploads

EXPOSE 5000

ENV FLASK_DEBUG=0

CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
