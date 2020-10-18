import numpy
import random

seed = 2
numpy.random.seed(seed)
# random.seed(seed)
random1 = []
for i in range(1,10):
    random1.append(random.randrange(100))
print(random1)

random.seed(3)
random2 = []
for i in range(1,10):
    random2.append(random.randint(1,10))
print(random2)

random.seed(1)
random2 = []
for i in range(1,10):
    random2.append(random.randint(1,10))
print(random2)

random.seed(1)
random3 = []
for i in range(1,10):
    random3.append(random.randint(1,10))
print(random3)