# Capstone Project

## Getting Started
These instructions will guide you through the steps used in the Capstone Project evaluation.

### Files

data-grant_time.csv : It contains the input dataset of the Grant messages collected during a given simulation using the IPACT algorithm.
delay.py: It returns descriptive statistics of the delay output from the simulator.
g-sim.py: The LR-PON simulator.
test_predictor.py : It runs the performance evaluation of a model varying the window of past observations and the number of predictions.
test_predictor.sh : It tests several models at the same time.

### Installing

pip install simpy, scipy, sklearn, pandas, matplotlib, statsmodels

### Evaluating model performance

Run the test_predictor.sh to test models' R² score and Mean Squared Error varying window (w=[10,20,30]) and number of predictions (p=[5,10,15,20]). In a terminal window run the following command:

```
bash test_predictor.sh
```
The command above runs parallel test_predictor.py for the models OLS (LinearRegression), Ridge and Lasso in background. After several minutes, one output file ("model"-report.txt) for each model is filled with the test's descriptive statistics of the metrics. The directory `counter` contains examples of each output file, as following: 

```
ls counter/
lasso-report.txt  ols-report.txt  ridge-report.txt
```
