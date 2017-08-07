import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from sklearn import linear_model
from sklearn.metrics import r2_score
from sklearn.metrics import mean_squared_error as mse
from sklearn.multioutput import MultiOutputRegressor
import time
import sys


def grant_predictor(onu_id,onu_df,window,predict,features,model,metric):
    index=0
    index_max = 0

    metric_list = []

    while index+window < len(onu_df):
        interval=index+window

        df_tmp = onu_df.iloc[index:interval]
        if interval+predict < len(onu_df):
            index_max = interval+predict
        else:
            index_max = len(onu_df)-1

        reg = MultiOutputRegressor(model)



        if len(features) == 1:
            X_pred = np.array(onu_df[features].iloc[interval:index_max]).reshape(-1,1)
            if len(X_pred) == 0:
                break
            reg.fit(np.array( df_tmp[features] ).reshape(-1,1) , df_tmp[['start','end']])
        else:
            X_pred = onu_df[features].iloc[interval:index_max]
            if len(X_pred) == 0:
                break
            reg.fit(df_tmp[features] , df_tmp[['start','end']])

        pred = reg.predict(X_pred)
        Y_true = onu_df[['start','end']].iloc[interval:index_max]
        metric_list.append(metric(Y_true, pred,multioutput='uniform_average'))

        index += predict

    return metric_list


model = sys.argv[1]
windows = [10,20,30]
predicts = [5,10,15,20]
#feature = ['timestamp','counter']
feature = ['counter']
models = {'ols': linear_model.LinearRegression(),'ridge': linear_model.Ridge(alpha=.5),'lasso':linear_model.Lasso(alpha=.1)}
metrics = {'r2': r2_score,'mse': mse}


table = {}

for w in windows:
    for p in predicts:
        table['{}-{}'.format(w,p)] = None


data = pd.read_csv("data-grant_time.csv")
for w in windows:
    for p in predicts:
        d = {'r2':None,'mse':None}
        for metric in metrics:
            result_list = []
            for onu in data['ONU_id'].unique():
                onu_df = data[ data['ONU_id'] == onu ][ ['timestamp','counter','start','end'] ]
                result = grant_predictor(onu,onu_df,w,p,feature,models[model],metrics[metric])
                result_list += result
            if metric == 'r2':
                d['r2'] = result_list
            else:
                d['mse'] = result_list
        table['{}-{}'.format(w,p)] = pd.DataFrame(d)

best_r2 = {'key': "",'r2':float("-inf")}
best_mse = {'key': "",'mse':float("inf")}


for k in table:
	print k
	print table[k].describe()
	print ""
	if table[k]['r2'].mean() > best_r2['r2']:
		best_r2['key'] = k
		best_r2['r2'] = table[k]['r2'].mean()
	if table[k]['mse'].mean() < best_mse['mse']:
		best_mse['key'] = k
		best_mse['mse'] = table[k]['mse'].mean()

print "best r2 = {}".format(best_r2)
print "best mse = {}".format(best_mse)
