# cql-fhir-search-data-extraction

This respository is meant to demonstrate how data can be extracted from a fhir server using CQL for initial cohort selection
and then using FHIR Search for the data extraction.

To test this you will need docker and docker-compose and python3 installed on your machine.

## How to use

Start up the blaze fhir server - `docker-compose up -d`
Wait for the server to start up - you can check in your browser if it is started up - `http://localhost:8081/fhir/Patient`
initialise the testdata - `bash init-testdata.sh`
execute the example data extraction script - `python3 example-data-extraction.py`