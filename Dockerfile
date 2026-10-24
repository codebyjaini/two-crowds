FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=8040
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY twocrowds ./twocrowds
COPY skill ./skill
COPY data/demo.json ./data/demo.json
COPY README.md .
EXPOSE 8040
CMD ["python", "-m", "twocrowds.cli", "serve"]
