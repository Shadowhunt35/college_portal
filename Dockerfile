FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create required directories
RUN mkdir -p logs static/uploads artifacts

# Environment
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["gunicorn", "app:create_app()", "--workers", "4", "--bind", "0.0.0.0:8000", "--timeout", "120"]