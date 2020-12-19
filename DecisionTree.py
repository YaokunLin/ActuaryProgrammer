# -*- coding: utf-8 -*-
"""
Created on Wed Dec  9 06:50:19 2020

@author: Yaokun Lin
"""

import numpy as np
import pandas as pd





class DecisionTree(object):
    def __init__(self,max_depth=float('inf'),min_samples_leaf=1):
        self.classValues =np.asfarray([])
        self.max_depth = max_depth
        self.min_samples_leaf =min_samples_leaf
        #The minimum number of samples required to be at a leaf node.
        # A split point at any depth will only be considered if it leaves at least min_samples_leaf training samples
        return
    
# Calculate the Gini index for a split dataset
    def gini_index(self, groups, classes):
    	# count all samples at split point
        
        SampleSize = (float(sum([len(group) for group in groups])))
        
        Gini = 0.0
        for group in groups:
            GroupSize = float(len(group))
            Group = np.array(group)
    
            ClassificationByGroup = Group[:,-1]       
            
            # avoid divide by zero
            if GroupSize == 0:
                continue
            GroupGini = 1.0
                              
            for ClassValue in classes:
                GroupGini = GroupGini-(np.sum((ClassificationByGroup == ClassValue).astype(np.float))/GroupSize)**2
                
            Gini = Gini + GroupSize/SampleSize * GroupGini # Weighted Avg of the Gini indeces of each group
           
        return Gini

    def get_Gini(self, leftYSplit, rightYSplit):
        leftGroupSize = float(len(leftYSplit))
        rightGroupSize = float(len(rightYSplit))

        leftGini = 1.0
        rightGini = 1.0

        if leftGroupSize !=0:
            for ClassValue in self.classValues:
                leftGini = leftGini - (np.sum((leftYSplit == ClassValue).astype(np.float)) / leftGroupSize) ** 2

        if rightGroupSize != 0:
            for ClassValue in self.classValues:
                rightGini = rightGini - (np.sum((rightYSplit == ClassValue).astype(np.float)) / rightGroupSize) ** 2

        return leftGroupSize/(leftGroupSize+rightGroupSize) * leftGini + rightGroupSize/(leftGroupSize+rightGroupSize) * rightGini # Weighted Avg of the Gini indeces of each group



# Select the best split point for a dataset
    def get_split(self, ColumnForSpliting, X, Y, rowValueInFeatureColumn):

        IsLeft=ColumnForSpliting<rowValueInFeatureColumn
        leftX=X[IsLeft]
        rightX=X[~IsLeft]

        leftY = Y[IsLeft].flatten()
        rightY = Y[~IsLeft].flatten()


        print(leftX)
        print(rightX)
        print(leftY)
        print(rightY)

        return leftX, rightX, leftY, rightY
    
    def train(self,X,Y):
        self.classValues = (np.unique(Y))
        self.grow_tree(X,Y,depth=1)



    def grow_tree(self, X,Y,depth):

        giniBeforeSplit = self.get_Gini(leftYSplit=np.asfarray([]),
                                    rightYSplit= Y)




        print(giniBeforeSplit)
        print('to start')
        print(depth)
        print(" ")

        if  giniBeforeSplit != 0.0 and depth<=self.max_depth:
            ## when giniBeforeSplit equals zero, no need to split future, it is already a perfect split, gini can't be improved
            splitFeatureColumnID, \
            featureValueCorrespondsToThesplitFeatureColumn, \
            giniAfterSplit, \
            splitLeftXgroup, \
            splitRightXgroup, \
            splitLeftYgroup, \
            splitRightYgroup = \
                self.split_selector(X=X, Y=Y, initialGinit=giniBeforeSplit)

            print(giniAfterSplit)
            print('to end')
            print(" ")

            if giniAfterSplit < giniBeforeSplit:
                print('left starts')
                print(splitLeftXgroup)
                print(splitLeftYgroup)
                if len(splitLeftYgroup)>=self.min_samples_leaf:
                    self.grow_tree(X=splitLeftXgroup, Y=splitLeftYgroup, depth=depth + 1)

                print('right starts')
                print(splitRightXgroup)
                print(splitRightYgroup)
                if len(splitRightYgroup) >= self.min_samples_leaf:
                    self.grow_tree(X=splitRightXgroup, Y=splitRightYgroup, depth=depth + 1)




    def split_selector(self,X,Y,initialGinit):

        bestGini = initialGinit
        bestFeatureID=-1.0
        bestfeatureValueCorrespondsToTheBestFeature = None
        bestLeftXgroup = np.asfarray([])
        bestLeftYgroup = np.asfarray([])
        bestRightXgroup = np.asfarray([])
        bestRightYgroup = np.asfarray([])


        for ithFeature in range (1,X.shape[1]+1,1):

            eachFeatureColumn = self.columnArray(matrix = X, ithColumn = ithFeature-1)

            for eachRow in eachFeatureColumn:
                leftXgroup, rightXgroup,leftYgroup, rightYgroup=self.get_split(ColumnForSpliting=eachFeatureColumn,
                                             X=X,
                                             Y=Y,
                                             rowValueInFeatureColumn=eachRow)
                currentGini = self.get_Gini(leftYSplit=leftYgroup,
                                    rightYSplit= rightYgroup)
                if(currentGini<bestGini):
                    bestGini = currentGini
                    bestFeatureID = ithFeature
                    bestfeatureValueCorrespondsToTheBestFeature=eachRow
                    bestLeftXgroup = leftXgroup
                    bestRightXgroup = rightXgroup
                    bestLeftYgroup = leftYgroup
                    bestRightYgroup=rightYgroup

                print(ithFeature)
                print(eachRow)
                print(self.get_Gini(leftYSplit=leftYgroup,
                                    rightYSplit= rightYgroup))

                print("")

        print('done')
        print('done')
        print('done')
        print(bestGini)
        print(bestFeatureID)
        print(bestfeatureValueCorrespondsToTheBestFeature)

        return bestFeatureID,bestfeatureValueCorrespondsToTheBestFeature,bestGini,bestLeftXgroup,bestRightXgroup,bestLeftYgroup,bestRightYgroup


            
    def columnArray(self, matrix, ithColumn):
        return np.asfarray([row[ithColumn] for row in matrix])
        
df=pd.read_csv('Train.csv')
x_train = np.asfarray(df.loc[:,(df.columns != 'C')])
y_train = np.asfarray(df.loc[:,(df.columns == 'C')])
del df

myTree = DecisionTree()
myTree.train(X = x_train, Y = y_train)

#print(myTree.gini_index([[[1, 0], [1, 0]], [[1, 1], [1, 1]]], [0, 1]))