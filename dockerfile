FROM python:3.8-slim-buster
WORKDIR /app
COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY bot_models.py . 
COPY exceptions.py .
COPY i_homeworks.py .
ENTRYPOINT ["python"]
CMD ["i_homeworks.py"]
