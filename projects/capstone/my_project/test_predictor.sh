#!/bin/bash


for model in "ols" "ridge" "lasso"
do
python test_predictor.py $model > $model-report.txt &
done
