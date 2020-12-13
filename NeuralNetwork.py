# -*- coding: utf-8 -*-
"""
Created on Sun Nov 22 11:56:36 2020

@author: Yaokun Lin
"""
import pandas as pd
import numpy as np
import random



class Network(object):
#eg. net = Network([2, 3, 1]) 
#represents a three layers network
#where the first layer to be the input layer with two neurons, 
#the input layer does not have weights and biases
#the 2nd layer is the hidden layer which has 3 neurons
#the 3rd layer is the output layer which has only 1 neuron


    def __init__(self, sizes, activation_function = 'sigmoid', learning_rate = .05, required_training_accuracy = 0.97, mini_batch_size=10):
        self.num_layers = len(sizes)
        self.sizes = sizes
        self.biases = [np.random.randn(y, 1) for y in sizes[1:]]
        #one bias for each of the nerons in the hidden layers and the output layer 
        #np.random.randn generates standard normal random variables
        #which provide starting points for the biases
        self.weights = [np.random.randn(y, x) 
                        for x, y in zip(sizes[:-1], sizes[1:])]
        #weights are applied between the input layer to the 1st hidden layer
        #applied between each of the hidden layers
        #applied between the final hidden layer to the the output layer 
        #np.random.randn generates standard normal random variables
        #which provide starting points for the weights
        self.activation_function = activation_function
        #default = "sigmoid", options include "softplus" and "ReLu"
        self.learning_rate=learning_rate
        self.required_training_accuracy = required_training_accuracy #Allows the algorithm go through epoches until it reaches the required level of accuracy
        self.mini_batch_size=mini_batch_size
        self.mini_step_rate = self.learning_rate / self.mini_batch_size
    
    
    def train(self, X,Y):
             
        ithEpoch = 1
        inSampleAccuracy = 0.00
        while inSampleAccuracy < self.required_training_accuracy:
            
            shuffledIndexs = np.asarray(range(0,len(X),1))
            random.shuffle(shuffledIndexs)
            numberOfCorrectForEachEpoch = 0
                     
            for kthMiniBatch in range(0, len(X), self.mini_batch_size):
                for index in shuffledIndexs[kthMiniBatch : kthMiniBatch+self.mini_batch_size]:
                  #  print(index)
                    
                    #gradien decent and backpropagation
                    self.backpropagation(X=X[index],
                                    Y=Y[index])
                    
                    
                    #in sample prediction, fitting evluation starts
                    IsCorrect = self.InSampleFittingEvaluator(X=X[index],
                                    Y=Y[index])                
                    
                    if IsCorrect:
                        numberOfCorrectForEachEpoch = numberOfCorrectForEachEpoch+1
                    #in sample prediction, fitting evluation ends
                                                                                       
            
            inSampleAccuracy = numberOfCorrectForEachEpoch/len(X)
            print(f"Epoch {ithEpoch}: {numberOfCorrectForEachEpoch} / {len(X)}, insample acc. {inSampleAccuracy*100:.2f}% ")
                     
            ithEpoch=ithEpoch+1
            
        print(f"Training completed, {ithEpoch-1} epochs were run, the current learning accuracy:{inSampleAccuracy*100:.2f}% higher than the required accuracy:{self.required_training_accuracy*100:.2f}%")
         
    def backpropagation(self,X,Y):
        
        zs,activations=self.feedforward(X)
               
        ##Backward passing Starts
        yOne = Y.reshape((len(Y),1))                
        
        SSEPrimeOne = self.cost_derivative(activations[-1],yOne)            
        
        sigmoidPrimeOne = self.sigmoid_prime(zs[-1])
        
        #delta = SSEPrimeOne*sigmoidPrimeOne
        
        LastBiasGradient = SSEPrimeOne*sigmoidPrimeOne
        
        LastWeightGradient=np.dot(LastBiasGradient, activations[-2].transpose())
        
        ###Updating the weights and biases in the very last layer 
        self.weights[-1] = np.add(self.weights[-1],-1 * self.mini_step_rate*LastWeightGradient)  
        self.biases[-1] = np.add(self.biases[-1],-1 * self.mini_step_rate*LastBiasGradient) 
                       
        
        ###Updating the weights and biases in the 2nd last layer To the 2nd layer 
        nthLastLayer = -2 #-2 indicates the 2nd last layer
        nthLastLayerBiasGradient = LastBiasGradient
        while nthLastLayer != -(self.num_layers-1):
            
            #gradient decent
            nthLastLayerBiasGradient = np.dot(self.weights[nthLastLayer+1].transpose(),nthLastLayerBiasGradient)
            nthLastLayerBiasGradient=nthLastLayerBiasGradient*self.sigmoid_prime(zs[nthLastLayer])
                       
            nthLastWeightGradient = np.dot(nthLastLayerBiasGradient,activations[nthLastLayer-1].transpose())
            
            
            self.biases[nthLastLayer] = np.add(self.biases[nthLastLayer],-1 * self.mini_step_rate*nthLastLayerBiasGradient)
            self.weights[nthLastLayer] = np.add(self.weights[nthLastLayer],-1 * self.mini_step_rate*nthLastWeightGradient)
            
            nthLastLayer = nthLastLayer-1 #Move Backward through Layers
                                   
        ###Updating the weights and biases in the 1st layer
        FirstBiasGradient = np.dot(self.weights[1].transpose(),nthLastLayerBiasGradient)
        FirstBiasGradient=FirstBiasGradient*self.sigmoid_prime(zs[0])
               
        FirstWeightGradient= np.dot(FirstBiasGradient,X.reshape((len(X),1)).transpose())
        
        self.biases[0] = np.add(self.biases[0],-1 * self.mini_step_rate*FirstBiasGradient) # updating the last layer
        self.weights[0] = np.add(self.weights[0],-1 * self.mini_step_rate*FirstWeightGradient) # updating the last layer
        ##Backward passing Ends
        
        
        return activations[-1]
        
        
    
    def softplus(self,z): #softplus(also called logistic) activation function
        return np.log(1.0+np.exp(z))
    
    def ReLu(self,z): #ReLu bent line activation function
        return np.max(0,z)                     
        
    def sigmoid(self,z): #sigmoid activation function
        return 1.0/(1.0+np.exp(-z))
    
    def sigmoid_prime(self,z):
        """Derivative of the sigmoid function."""
        return self.sigmoid(z)*(1-self.sigmoid(z))
    
    def cost_derivative(self, output_activations, y):
        """Return the vector of partial derivatives \partial C_x /
        \partial a for the output activations."""
        return 2*(output_activations-y)
    
    def feedforward(self, X):
        """Return the output of the network if "a" is input."""
        # for b, w in zip(self.biases, self.weights):
        #     if self.activation_function == 'softplus':
        #         a = self.softplus(np.dot(w, a)+b)
        #     elif self.activation_function == 'ReLu':
        #         a = self.ReLu(np.dot(w, a)+b)
        #     else:
        #         a= self.sigmoid(np.dot(w, a)+b)
        
        ##Feedforward Starts
        ###Feedforward in the 1st layer
        z=np.dot(self.weights[0],X)
        z=z.reshape((len(z),1))
        z = np.add(z,self.biases[0])
        activation = self.sigmoid(z)
        
        
        activations = [activation] # list to store all the activations, layer by layer
        zs = [z] # list to store all the z vectors, layer by layer
        
        
        ###Feedforward in the 2nd layer to the last layer
        nthLayer = 1 
        while nthLayer < self.num_layers-1:
         
            z = np.dot(self.weights[nthLayer],activation)        
            z = np.add(z,self.biases[nthLayer])
          
            zs.append(z)
                   
            activation=self.sigmoid(z)           
            activations.append(activation)
            
            nthLayer=nthLayer+1
        ##Feedforward Ends
        return zs,activations
    
    def InSampleFittingEvaluator(self, X, Y): 
        finalOutputZs,finalOutpuActivations=self.feedforward(X=X)
        
        xInSamplePredicted = np.argmax(finalOutpuActivations[-1])     
        yLable = np.argmax(Y)
        
        return xInSamplePredicted == yLable
    
    def predict(self,X, IsReturnPredictionPbty = True):
        predicted_zs,predicted_activations = self.feedforward(X)
        
        if IsReturnPredictionPbty:
            self.PrintPredictionPbty(predicted_activations[-1])
          
        return np.argmax(predicted_activations[-1])
    
     
    def PrintPredictionPbty(self,FinalActivationArray):
        FinalActivationList = list(FinalActivationArray)
        totalSum = np.sum(FinalActivationArray)
        
        for num in FinalActivationList:
           
            pbty = str(round(float(num/totalSum*100),2))+"%"
            print(f"number {FinalActivationList.index(num)}'s pred. pbty:{pbty}")
        
        print(' ')
        
    
    
#Loading training data starts
df=pd.read_csv('mnist_train.csv')
#The images of the MNIST dataset are greyscale and the pixels range between 0 and 255 including both bounding values. 
#We will map these values into an interval from [0.01, 1] by multiplying each pixel by 0.99 / 255 and 
#adding 0.01 to the result. This way, we avoid 0 values as inputs, which are capable of preventing weight updates
x_train = np.asfarray(df.loc[:,(df.columns != 'label')])*0.99 / 255+.01
y_train = np.asfarray(df.loc[:,(df.columns == 'label')])
del df

#We need the labels in our calculations in a one-hot representation. 
lr = np.arange(10)
for label in range(10):
    one_hot = ((np.arange(10))==label).astype(np.int)
    print("label: ", label, " in one-hot representation: ", one_hot)
del one_hot,label

#easier to calculate 0.01 and 0.99
y_train = (y_train==lr).astype(np.float)
y_train[y_train ==1] = 0.99
y_train[y_train ==0] = 0.01

#Training the model
#SkyNet = Network([784,25,30, 10],activation_function='sigmoid', learning_rate = 5, epochs = 25, mini_batch_size=10)
SkyNet = Network([784,25,30, 10],activation_function='sigmoid', learning_rate = 5, required_training_accuracy = 0.95, mini_batch_size=10)
SkyNet.train(X=x_train,Y=y_train)
#del x_train,y_train



#Loading testing data
df=pd.read_csv('mnist_test.csv')
x_test = np.asfarray(df.loc[:,(df.columns != 'label')])*0.99 / 255+.01
# y_test = np.asfarray(df.loc[:,(df.columns == 'label')])
#del df

# y_test = (y_test==lr).astype(np.float)
# y_test[y_test ==1] = 0.99
# y_test[y_test ==0] = 0.01
del lr

#Select an out sample handwritten digit to predict
selected_OutSample_X = x_test[102]

#show imagine Example on a plot
import matplotlib.pyplot as plt
img = selected_OutSample_X.reshape((28,28))
plt.imshow(img, cmap="Greys")    
plt.show()    
del img

#use neural network to make prediction

print(SkyNet.predict(selected_OutSample_X,IsReturnPredictionPbty = True))
print("IS THE PREDICTED OUT_SAMPLE_X BASED ON above PROBABILITIES")




    