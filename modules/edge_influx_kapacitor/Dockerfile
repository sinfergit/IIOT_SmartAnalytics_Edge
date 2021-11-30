# Full tag list: https://hub.docker.com/r/library/kapacitor/tags/
FROM kapacitor:latest

# Install python
RUN apt-get -qq update && apt-get -qq install -y \
    python3 \
    python3-pip

# Install python dependencies
RUN pip3 install \
	numpy \
	pandas \
	protobuf==3.18.0\
	scipy

# Install git
RUN apt-get -qq install -y git

# Install kapacitor agent
RUN git clone https://github.com/influxdata/kapacitor.git /tmp/kapacitor

# Set the working directory
# WORKDIR /tmp/kapacitor_udf

# Copy the UDF Python files ,ML model files into the kapacitor directory
COPY ./udfs/ /tmp/kapacitor_udf/

# Start kapacitor service (log-level: debug | info | error)
CMD ["kapacitord","-log-file","/etc/kapacitor/kapacitor.log","-log-level","info"]