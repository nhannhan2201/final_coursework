#!/bin/bash
cd ../..
docker build -t nhannguyen2201/drift-api:0.0.1 -f apps/drift-api/Dockerfile .
docker push nhannguyen2201/drift-api:0.0.1
