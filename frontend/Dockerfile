FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV BACKEND_URL=http://backend:8000
ENV SECRET_KEY=gamis-super-secret-key-999

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
