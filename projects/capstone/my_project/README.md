# Capstone Project

This project compares the average packet delay of the traditional Dynamic Bandwidth Allocation (DBA) algorithm, called IPACT and the proposed DBA alorithm, called PD-DBA, which uses Machine Learning to predict next cycle Grant messages.

## Getting Started
These instructions will guide you through the steps used in the Capstone Project evaluation. 

### Files

`data-grant_time.csv`: It contains the input dataset of the Grant messages collected during a given simulation using the IPACT algorithm.

`delay.py`: It returns descriptive statistics of the delay output from the simulator.

`g-sim.py`: The LR-PON simulator.

`test_predictor.py`: It runs the performance evaluation of a model varying the window of past observations and the number of predictions.

`test_predictor.sh`: It tests several models at the same time.

### Installing

pip install simpy, scipy, sklearn, pandas, matplotlib, statsmodels

### Evaluating model performance

Run the test_predictor.sh to test models' R² score and Mean Squared Error varying window (`w=[10,20,30]`) and number of predictions (`p=[5,10,15,20]`). In a terminal window run the following command:

```
bash test_predictor.sh
```
The command above runs parallel test_predictor.py for the models OLS (LinearRegression), Ridge and Lasso in background. After several minutes, one output file ("model"-report.txt) for each model is filled with the test's descriptive statistics of the metrics. The directory `counter` contains examples of each output file, as following: 

```
ls counter/
lasso-report.txt  ols-report.txt  ridge-report.txt
```

### Run the simulator

The best model is implemented in the class PD_DBA at line 493. Edit this line in g-sim.py if you want to change model.

First simulate the IPACT algorithm:

```
python g-sim.py ipact -O 3 -o ipact
```

Then, simulate the PD-DBA algorithm with the parameters 'w' and 'p':

```
python g-sim.py pd_dba -O 3 -w 10 -p 5 -o pd_dba
```

Run the following commands to display the delay statistics of each algorithm:

```
$ python delay.py ipact-delay.csv 
count    207895.000000
mean          0.007644
std           0.001590
min           0.001373
25%           0.006365
50%           0.007563
75%           0.008807
max           0.014445
Name: delay, dtype: float64
```

```
$ python delay.py pd_dba-delay.csv 
count    207903.000000
mean          0.005758
std           0.002668
min           0.000000
25%           0.003869
50%           0.005722
75%           0.007486
max           0.029095
Name: delay, dtype: float64
```

'


