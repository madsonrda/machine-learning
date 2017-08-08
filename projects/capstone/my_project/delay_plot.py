import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os, errno
import sys

try:
    os.makedirs('img')
except OSError as e:
    if e.errno != errno.EEXIST:
        raise


IPACT = {}
PD_DBA = {}


load = [25,31,37,43,50,56,62,68,75,81,87,93]
exponents = [1160, 1450, 1740, 2030, 2320, 2610, 2900, 3190, 3480, 3770, 4060, 4350]
seeds = [20,30,40,50,60,70,80,90,100,110]
parameters = [{'w':10,'p':5},{'w':20,'p':20}]


for param in parameters:
    PD_DBA['{}-{}'.format(param['w'],param['p'])] = {}

for exp in exponents:

    ipact = []
    for seed in seeds:
        df_tmp = pd.read_csv("csv/delay/ipact-3-27000-0-100-{}-{}-delay.csv".format(seed, exp))
        ipact.append(df_tmp['delay'].mean()*1000)
    IPACT[exp] = [np.mean(ipact),np.std(ipact)]


for param in parameters :
    for exp in exponents:
        pd_dba = []
        for seed in seeds:
            df_tmp = pd.read_csv("csv/delay/pd_dba-3-27000-0-100-{}-{}-{}-{}-delay.csv".format(seed,exp,param['w'],param['p']))
            pd_dba.append(df_tmp['delay'].mean()*1000)
        PD_DBA['{}-{}'.format(param['w'],param['p'])][exp] = [np.mean(pd_dba),np.std(pd_dba)]

ipact_df = pd.DataFrame(IPACT)
pd_dba_df = pd.DataFrame(PD_DBA)


plt.figure()

title = sys.argv[1]
plt.title(title)
plt.xlabel("load (%)")
plt.ylabel("delay (ms)")


plt.errorbar(load, ipact_df.iloc[0],ipact_df.iloc[1],color="k", linestyle='None')
plt.plot(load, ipact_df.iloc[0], 'o-', color="k",label="IPACT")


number = 4
cmap = plt.get_cmap('gnuplot')
colors = [cmap(i) for i in np.linspace(0.25, 1, number)]
print len(colors)

for j, param in enumerate(parameters):
    array = np.array([ i for i in pd_dba_df['{}-{}'.format(param['w'],param['p'])].iloc[:] ])

    plt.errorbar(load, array[:,0],array[:,1], color=colors[j],linestyle='None')
    plt.plot(load, array[:,0], '->',color=colors[j] ,label="PD-DBA w={} p={}".format(param['w'],param['p']))

plt.legend(loc='upper center', shadow=True)
plt.savefig("img/Delay-"+title)
