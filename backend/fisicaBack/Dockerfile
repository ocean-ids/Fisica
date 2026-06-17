FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN python - <<'PY'
from pathlib import Path
import codecs

data = Path('requirements.txt').read_bytes()
if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
    text = data.decode('utf-16')
else:
    text = data.decode('utf-8')

Path('requirements-utf8.txt').write_text(text, encoding='utf-8')
PY
RUN pip install --no-cache-dir -r requirements-utf8.txt \
    && pip install --no-cache-dir gunicorn

COPY . /app

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn fisicaBack.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 900 --graceful-timeout 900"]
