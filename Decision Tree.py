import numpy as np
import pandas as pd
import math

from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter


class DecisionTree():
    def __init__(self, x, y,  idxs = None, min_leaf=0,depth=0, max_depth = 0):
        if idxs is None: idxs=np.arange(len(y))
        #if depth is None: depth=0
        #idxs === array[0,1,2,...,len(y)-1]
        self.x,self.y,self.idxs,self.min_leaf,self.depth,self.max_depth = x,y,idxs,min_leaf,depth,max_depth
        self.n,self.c = len(idxs), x.shape[1]
        #c===number of columns/features in a leave===5 to start in this case which are ['school','sex','age','address','absences']
        #n===number of rows/observations in a leave===649 to start===number of students
        self.val = np.mean(y[idxs])
        #val===avg value of the y colum in the node, this is for prediction

        self.score = float('inf')
        if self.depth<self.max_depth: self.find_varsplit() #when it is at the max_depth, no need for any splits

    def find_varsplit(self):
       for i in range(self.c): self.find_better_split(i)
       #range(self.c) = array[0,1,2,...,Column Number(X)-1]
       # loop through all the columns/features and run "self.find_better_split" on each of the columns/features
       #self.find_better_split(i) is to find the best split point within a particular column
       if self.score == float('inf'): return
       # when self.score= infinity it indicates the score calculation hasn't been computed, so it is a leave, no need to go through the rest of the function
       x = self.split_col
       #self.split_col=== the unsorted column which was used to do the spliting === the split column which produce the best score
       #'school' is the first column used for the spliting in the example
       lhs = np.nonzero(x <= self.split)[0]
       #seprate the best spliting column values that are smaller than the spliting point to the LHS
       rhs = np.nonzero(x > self.split)[0]
       # best spliting column values that are greater than the spliting point to the LHS
   #    str=('')
    #   for i in range(1,self.depth+1+1): str=str+" "
     #  print(str+'L')
       self.lhs = DecisionTree(self.x, self.y, self.idxs[lhs],min_leaf=self.min_leaf,depth=self.depth+1,max_depth=self.max_depth)
       #iteraively call the object constructor to build leaves
       #self.idxs[lhs] is to select a specific portion of the data into the DecisionTree() iterations
   #    str = ('')
    #   for i in range(1, self.depth + 1 + 1): str = str + " "
     #  print(str + 'R')
       self.rhs = DecisionTree(self.x, self.y, self.idxs[rhs],min_leaf=self.min_leaf,depth=self.depth+1,max_depth=self.max_depth)

    def find_better_split(self, var_idx):
        #var_inx === the index of the column being examinated
        x, y = self.x.values[self.idxs, var_idx], self.y[self.idxs]
        #x===the specific column being examinated, with the data portion correponds to self.idxs
        #y===the y column, with the data portion correponds to self.idxs
        sort_idx = np.argsort(x)
        #sort_idx === sorting X in an accending order and return the indices of the sorted X
        sort_y, sort_x = y[sort_idx], x[sort_idx]
        #the sorting depends on the X column being examinated
        rhs_cnt, rhs_sum, rhs_sum2 = self.n, sort_y.sum(), (sort_y ** 2).sum()
        #initilization
        #rhs_cnt=== observation count on the right hand side, it is 649 to start === the total number of obervations in this example
        #rhs_sum === the total sum of the y value on the right hand side
        #rhs_sum2 === the total sum of the square of the y value on the right hand side

        lhs_cnt, lhs_sum, lhs_sum2 = 0, 0., 0.
        #initilization



        for i in range(0, self.n - self.min_leaf - 1): # loops through the rows in the column being examinated
            #range(0, self.n - self.min_leaf - 1) is to make sure there will be at least (self.min_leaf) observations sitting in one of the leaves
            #the initial === range(0, 646) = range (0, 649-2-1)
            xi, yi = sort_x[i], sort_y[i]
            #xi goes through the selected x column in an accending order, except for the last two elements as we need at least (self.min_leaf) observations sitting in one of the leaves
            #yi goes through the y column in x's accending order

            lhs_cnt += 1 # when we move one observation from the RHS to the LHS, we add it to the LHS count
            rhs_cnt -= 1 # when we move one observation from the RHS to the LHS, we minus it from the RHS count
            lhs_sum += yi # when we move one observation from the RHS to the LHS, we add the value to the LHS total sum
            rhs_sum -= yi # when we move one observation from the RHS to the LHS, we minus the value from the RHS total sum
            lhs_sum2 += yi ** 2
            rhs_sum2 -= yi ** 2
            if i < self.min_leaf or xi == sort_x[i + 1]:
                continue
            # when the number of the observations is less than self.min_leaf, no need to compute the score
            # when the next xi is the same as the current xi, no need to compute the score again, as the split point will be the same and the score is the same

            lhs_std = std_agg(lhs_cnt, lhs_sum, lhs_sum2)
            #lhs_std====math.sqrt((lhs_sum2/lhs_cnt) - (lhs_sum/lhs_cnt)**2)=== the stand. deviation of the y observations in the LHS
            rhs_std = std_agg(rhs_cnt, rhs_sum, rhs_sum2)
            #the stand. deviation of the y observations in the RHS
            curr_score = lhs_std * lhs_cnt + rhs_std * rhs_cnt
            #curr_score = the score for the current split = weighted avg. of the stand. deviations of both sides
            # the lower the stand. deviation = the observations within the leave are more alike, the split is better

            if curr_score < self.score:
                self.var_idx, self.score, self.split = var_idx, curr_score, xi
            # when the the current score is better than the prior best score, updating self.score as the best score, and updating the split point

    @property
    def split_name(self):
        return self.x.columns[self.var_idx]

    @property
    def split_col(self):
        #print(self.idxs)
        #print(self.var_idx)
        #print(self.x.values)
        return self.x.values[self.idxs, self.var_idx]

    @property
    def is_leaf(self):
        return self.score == float('inf')
        #when the score is infinity, there has been no computing of the score in that level, so it is a leaf

    def __repr__(self):
        s = f'n: {self.n}; val:{self.val}'
        if not self.is_leaf:
            s += f'; score:{self.score}; split:{self.split}; var:{self.split_name}'
        return s

    def predict(self, x):
        return np.array([self.predict_row(xi) for xi in x]) #predicts each observation individually

    def predict_row(self, xi):
        if self.is_leaf: return self.val # if it is at the terminal leave, returns the final prediction
        t = self.lhs if xi[self.var_idx] <= self.split else self.rhs #this directs the observation to the right leaves
        return t.predict_row(xi) #recursivly call itself until it reaches a terminal leave

def std_agg(cnt, s1, s2): return math.sqrt((s2/cnt) - (s1/cnt)**2)

df=pd.read_csv('data.txt')
X=df.loc[:,['school','sex','age','address','absences']]
Y=np.asarray(df.G1+df.G2+df.G3)

X=pd.get_dummies(X, columns=['school','sex','address'],drop_first=True)

#print(X.shape) #(649, 5)
#print(Y.shape) #(649,)


#print(X)


PortionForTesting=0.2
curOff=int(PortionForTesting*len(df))

X_Test=X[:curOff]
Y_Test=Y[:curOff]

X_Train=X[curOff:]
Y_Train=Y[curOff:]

#print(len(X_Train))
#print(len(Y_Train))

#print(X_Test)
#print(X_Train)

X_TesttoList=X_Test.values.tolist()


MinLeaveList=[]
Max_DepthList=[]
OutSampleMAEList=[]


for eachMinLeave in range(51):
    for eachMax_depth in range(2,101):
        tree = DecisionTree(X_Train, Y_Train, min_leaf=eachMinLeave, max_depth=eachMax_depth)
        #loop through the combination of min_leaf and max_depth to find the combination that generate the best out of sample prediction
        y_Test_hat = np.asarray(tree.predict(X_TesttoList))
       # print(eachMinLeave,eachMax_depth)
       # print(np.mean(np.abs(y_Test_hat - Y_Test)) / np.mean(Y_Test))

        MinLeaveList.append(eachMinLeave)
        Max_DepthList.append(eachMax_depth)
        OutSampleMAEList.append(np.mean(np.abs(y_Test_hat - Y_Test)) / np.mean(Y_Test))


MinLeaveArray=np.asarray(MinLeaveList)
Max_DepthArray=np.asarray(Max_DepthList)
OutSampleMAEArray=np.asarray(OutSampleMAEList)

# Plot the surface.
fig = plt.figure()
ax = fig.gca(projection='3d')
X = np.arange(0, 51)
Y = np.arange(2, 101)
X, Y = np.meshgrid(X, Y)
Z = OutSampleMAEArray.reshape(X.shape)


#print(X)
#print(X.shape)
#print(Y.shape)
#print(Z.shape)



surf = ax.plot_surface(X, Y, Z, cmap=cm.coolwarm,
                       linewidth=0, antialiased=False)

# Add a color bar which maps values to colors.
fig.colorbar(surf, shrink=0.5, aspect=5)

ax.set_xlabel('Min_Leave_Sample')
ax.set_ylabel('Max_Depth')
ax.set_zlabel('Out_Sample_MAE')

plt.show()



del df




#['school;sex;age;address;famsize;Pstatus;Medu;Fedu;Mjob;Fjob;reason;guardian;traveltime;studytime;failures;schoolsup;famsup;paid;activities;nursery;higher;internet;romantic;famrel;freetime;goout;Dalc;Walc;health;absences;G1;G2;G3']

