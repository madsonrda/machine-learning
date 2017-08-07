#!/bin/bash

for target in "start" "end" 
do
   for model in "ols" "ridge" "lasso"
   do
      python test_predictor.py $target $model > $target-$model-report.txt &
   done
done
