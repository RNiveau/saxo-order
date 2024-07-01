#! /bin/bash

date=$(date +%s)
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin 829357598265.dkr.ecr.eu-west-1.amazonaws.com
docker build --platform linux/amd64 -t 829357598265.dkr.ecr.eu-west-1.amazonaws.com/k-order:${date} . \
&& docker push 829357598265.dkr.ecr.eu-west-1.amazonaws.com/k-order:${date} \
&& echo New image is: 829357598265.dkr.ecr.eu-west-1.amazonaws.com/k-order:${date} \
&& (cd pulumi && GODEBUG=asyncpreemptoff=1 pulumi config set image-tag ${date}) \
&& (cd pulumi && GODEBUG=asyncpreemptoff=1 pulumi up)
