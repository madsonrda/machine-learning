#!/bin/bash

for seed in 20 30 40 50 60 70 80 90 100 110
do
   for exp in 1160 1450 1740 2030 2320 2610 2900 3190 3480 3770 4060 4350
   do
      python g-sim.py pd_dba -O 3 -s $seed -e $exp -w 10 -p 5 &
   done
   sleep 100
done

for seed in 20 30 40 50 60 70 80 90 100 110
do
   for exp in 1160 1450 1740 2030 2320 2610 2900 3190 3480 3770 4060 4350
   do
      python g-sim.py pd_dba -O 3 -s $seed -e $exp -w 20 -p 20 &
   done
   sleep 100
done
