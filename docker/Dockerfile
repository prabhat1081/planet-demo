FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y virtualenv

# Create a virtualenv for dependencies. This isolates these packages from
# system-level packages.
# Use -p python3 or -p python3.7 to select python version. Default is version 2.
RUN virtualenv /env -p python3.11

# Setting these environment variables are the same as running
# source /env/bin/activate.
ENV VIRTUAL_ENV=/env
ENV PATH=/env/bin:$PATH

# Install dependencies
ADD requirements.txt /app/
RUN pip3 install -r requirements.txt

# Add application code
ADD code/ /app

# Set the entrypoint to run Streamlit
ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port", "8080"]