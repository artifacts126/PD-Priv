# PD-Priv


## Getting started

zkay_interface (zeestar interfaces compatible with PD-Priv)

test (all test contracts)

transform_zkay_for_consistency (Privacy-focused upgrading: zk-upgrading)

source_and_victim_analysis (Privacy-focused upgrading: elimination of source variables)

```
#Evaluation of zk-upgrading
cd test/eval_dynamiczk_sp2022 
python benchmark.py

cd test/eval_dynamiczk_SWC136 
python benchmark.py

#Evaluation of elimination of source variables
cd source_and_victim_analysis   
python benchmark.py  
```