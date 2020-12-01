# The base image we want to inherit from
FROM python:3
ENV PYTHONUNBUFFERED 1

RUN mkdir /peerlogic
WORKDIR /peerlogic

# using ADD with the requirements (vs copy) makes use of caching to speed up consecutive builds
ADD ./requirements requirements

# Install the pip requirements file depending on
# the uncommitted .env file passed in when starting build.
RUN pip install -Ur requirements/requirements.txt

# Copy the rest of our application.
COPY . .

# Expose the application on port 8000 (check if container run or compose needs to map to 8000 locally)
EXPOSE 8000
# Run test server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
