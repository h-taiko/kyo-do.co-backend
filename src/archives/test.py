# coding: UTF-8
from __future__ import print_function

import json,logging,re

temp = "Bearer thisIsKey"
pattern = r"Bearer"

if re.search(pattern, temp) is not None :
    print("hoge")
else:
    print("Bearerrなし")
    
print(temp.replace("Bearer","").replace(" ",""))