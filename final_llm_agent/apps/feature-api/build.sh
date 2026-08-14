#!/bin/bash
cd ../..
docker build -t nhannguyen2201/feature-api:0.0.1 -f apps/feature-api/Dockerfile .
docker push nhannguyen2201/feature-api:0.0.1
