FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN SECRET_KEY=build-only AWS_ACCESS_KEY_ID=build-only AWS_SECRET_ACCESS_KEY=build-only \
    AWS_STORAGE_BUCKET_NAME=build-only AWS_S3_REGION_NAME=build-only GEMINI_API_KEY=build-only \
    DB_PASSWORD=build-only python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "student_ms.wsgi:application", "--bind", "0.0.0.0:8000"]
