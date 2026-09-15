#!/bin/bash
cd custom_jenkins
dockerhub_username="nhannguyen2201"
image_name="jenkins:lts"
docker build -t $dockerhub_username/$image_name .
docker push $dockerhub_username/$image_name