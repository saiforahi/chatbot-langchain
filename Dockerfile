FROM python:3.10-bullseye
WORKDIR /app
COPY . /app
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt
RUN flask --app main.py db init
RUN flask --app main.py db migrate
RUN flask --app main.py db upgrade
EXPOSE 5000
CMD python main.py