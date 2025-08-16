#!/bin/bash
# Push ke branch semasa

branch=$(git rev-parse --abbrev-ref HEAD)

git add .
git commit -m "update from server"
git push origin $branch

