FROM python:3.12.9-slim

WORKDIR /root/
COPY requirements.txt .

RUN python -m pip install --upgrade pip &&\
	pip install -r requirements.txt

#ENV URL_MODEL_SERVICE = localhost:8080

EXPOSE 8080

CMD ["python", "serve_model.py"]