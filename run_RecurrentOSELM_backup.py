# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2013-2015, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero Public License for more details.
#
# You should have received a copy of the GNU Affero Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

import csv
from optparse import OptionParser

from matplotlib import pyplot as plt
import numpy as np
#from hpelm import ELM

from swarm_runner import SwarmRunner
from scipy import random

import pandas as pd
from errorMetrics import *

from htmresearch.algorithms.FOS_ELM import FOSELM
from htmresearch.algorithms.ReOS_ELM import REOSELM
from htmresearch.algorithms.RecurrentOS_ELM import RecurrentOSELM
#plt.ion()

def initializeRecurrentOSELMnet(nDimInput, nDimOutput, numNeurons=100,BN=True,InWeightFF=0.999,OutWeightFF=0.999,HiddenWeightFF=0.999,PRINTING=True,ORTH=True,AE=True):
  # Build ELM network with nDim input units,
  # numNeurons hidden units (LSTM cells) and nDimOutput cells

  # net = ELM(nDimInput, nDimOutput)
  # net.add_neurons(numNeurons, "sigm")

  net = RecurrentOSELM(nDimInput, nDimOutput,
                       numHiddenNeurons=numNeurons,
                       activationFunction='sig',
                       BN=BN,
                       inputWeightForgettingFactor=InWeightFF,
                       outputWeightForgettingFactor=OutWeightFF,
                       hiddenWeightForgettingFactor=HiddenWeightFF,
                       ORTH=ORTH,
                       AE=AE)

  if PRINTING:
    print('----------Network Configuration-------------------')
    print('#input neuron = '+str(nDimInput))
    print('#output neuron = '+str(nDimOutput))
    print('#hidden neuron = '+str(numNeurons))
    print('Whitening = ' +str(BN))
    print('Orthogonalization = '+str(ORTH))
    print('Auto-encoding = '+str(AE))
    print('input weight forgetting factor = '+str(InWeightFF))
    print('output weight forgetting factor = ' + str(OutWeightFF))
    print('hidden weight forgetting factor = ' + str(HiddenWeightFF))
    print('---------------------------------------------------')

  return net



def readDataSet(dataSet):
  filePath = 'data/'+dataSet+'.csv'
  # df = pd.read_csv(filePath, header=0, skiprows=[1, 2], names=['time', 'data'])
  # sequence = df['data']

  if dataSet=='nyc_taxi':
    df = pd.read_csv(filePath, header=0, skiprows=[1,2],
                     names=['time', 'data', 'timeofday', 'dayofweek'])
    sequence = df['data']
    dayofweek = df['dayofweek']
    timeofday = df['timeofday']

    seq = pd.DataFrame(np.array(pd.concat([sequence, timeofday, dayofweek], axis=1)),
                        columns=['data', 'timeofday', 'dayofweek'])
  elif dataSet=='sine':
    df = pd.read_csv(filePath, header=0, skiprows=[1, 2], names=['time', 'data'])
    sequence = df['data']
    seq = pd.DataFrame(np.array(sequence), columns=['data'])
  else:
    raise(' unrecognized dataset type ')

  return seq


def getTimeEmbeddedMatrix(sequence, numLags=100, predictionStep=1,
                      useTimeOfDay=True, useDayOfWeek=True):
  print "generate time embedded matrix "
  print "the training data contains ", str(nTrain-predictionStep), "records"

  inDim = numLags + int(useTimeOfDay) + int(useDayOfWeek)

  if useTimeOfDay:
    print "include time of day as input field"
  if useDayOfWeek:
    print "include day of week as input field"

  X = np.zeros(shape=(len(sequence), inDim))
  T = np.zeros(shape=(len(sequence), 1))
  for i in xrange(numLags-1, len(sequence)-predictionStep):
    if useTimeOfDay and useDayOfWeek:
      sample = np.concatenate([np.array(sequence['data'][(i-numLags+1):(i+1)]),
                               np.array([sequence['timeofday'][i]]),
                               np.array([sequence['dayofweek'][i]])])
    elif useTimeOfDay:
      sample = np.concatenate([np.array(sequence['data'][(i-numLags+1):(i+1)]),
                               np.array([sequence['timeofday'][i]])])
    elif useDayOfWeek:
      sample = np.concatenate([np.array(sequence['data'][(i-numLags+1):(i+1)]),
                               np.array([sequence['dayofweek'][i]])])
    else:
      sample = np.array(sequence['data'][(i-numLags+1):(i+1)])

    X[i, :] = sample
    T[i, :] = sequence['data'][i+predictionStep]

  return (X, T)



def _getArgs():
  parser = OptionParser(usage="%prog PARAMS_DIR OUTPUT_DIR [options]"
                              "\n\nCompare TM performance with trivial predictor using "
                              "model outputs in prediction directory "
                              "and outputting results to result directory.")
  parser.add_option("-d",
                    "--dataSet",
                    type=str,
                    default='nyc_taxi',
                    dest="dataSet",
                    help="DataSet Name, choose from sine, SantaFe_A, MackeyGlass")

  # parser.add_option("-n",
  #                   "--predictionstep",
  #                   type=int,
  #             s      default=1,
  #                   dest="predictionstep",
  #                   help="number of steps ahead to be predicted")


  (options, remainder) = parser.parse_args()
  print options

  return options, remainder



def saveResultToFile(dataSet, predictedInput, algorithmName):
  inputFileName = 'data/' + dataSet + '.csv'
  inputFile = open(inputFileName, "rb")

  csvReader = csv.reader(inputFile)

  # skip header rows
  csvReader.next()
  csvReader.next()
  csvReader.next()

  outputFileName = './prediction/' + dataSet + '_' + algorithmName + '_pred.csv'
  outputFile = open(outputFileName, "w")
  csvWriter = csv.writer(outputFile)
  csvWriter.writerow(
    ['timestamp', 'data', 'prediction-' + str(predictionStep) + 'step'])
  csvWriter.writerow(['datetime', 'float', 'float'])
  csvWriter.writerow(['', '', ''])

  for i in xrange(len(sequence)):
    row = csvReader.next()
    csvWriter.writerow([row[0], row[1], predictedInput[i]])

  inputFile.close()
  outputFile.close()



if __name__ == "__main__":

  (_options, _args) = _getArgs()
  dataSet = _options.dataSet


  print "run ELM on ", dataSet
  SWARM_CONFIG = SwarmRunner.importSwarmDescription(dataSet)
  predictedField = SWARM_CONFIG['inferenceArgs']['predictedField']
  nTrain = SWARM_CONFIG["streamDef"]['streams'][0]['last_record']
  predictionStep = SWARM_CONFIG['inferenceArgs']['predictionSteps'][0]

  useTimeOfDay = False
  useDayOfWeek = False

  nTrain = 500
  numLags = 100

  # prepare dataset as pyBrain sequential dataset
  sequence = readDataSet(dataSet)

  # standardize data by subtracting mean and dividing by std
  meanSeq = np.mean(sequence['data'])
  stdSeq = np.std(sequence['data'])
  sequence['data'] = (sequence['data'] - meanSeq)/stdSeq

  meanTimeOfDay = np.mean(sequence['timeofday'])
  stdTimeOfDay = np.std(sequence['timeofday'])
  sequence['timeofday'] = (sequence['timeofday'] - meanTimeOfDay)/stdTimeOfDay

  meanDayOfWeek = np.mean(sequence['dayofweek'])
  stdDayOfWeek = np.std(sequence['dayofweek'])
  sequence['dayofweek'] = (sequence['dayofweek'] - meanDayOfWeek)/stdDayOfWeek

  (X, T) = getTimeEmbeddedMatrix(sequence, numLags, predictionStep,
                                 useTimeOfDay, useDayOfWeek)

  random.seed(6)

  net = initializeRecurrentOSELMnet(nDimInput=X.shape[1],
                                    nDimOutput=1,
                                    numNeurons=23,
                                    BN=True,
                                    InWeightFF=1,
                                    OutWeightFF=0.915,
                                    HiddenWeightFF=1,
                                    AE=True,
                                    ORTH=False)


  net.initializePhase(lamb = 0.0001)

  predictedInput = np.zeros((len(sequence),))
  targetInput = np.zeros((len(sequence),))
  trueData = np.zeros((len(sequence),))

  #ELMAE=REOSELM(X.shape[1],X.shape[1],1000,activationFunction='sig')
  #ELMAE.initializePhase(X[:nTrain,:],X[:nTrain:], lamb=0.0001)
  #net.inputWeights = ELMAE.beta
  #net.bias.fill(0)
  for i in xrange(nTrain, len(sequence)-predictionStep-1):
    net.train(X[[i], :], T[[i], :])
    Y = net.predict(X[[i+1], :])

    predictedInput[i+1] = Y[-1]
    targetInput[i+1] = sequence['data'][i+1+predictionStep]
    trueData[i+1] = sequence['data'][i+1]
    #print "Iteration {} target input {:2.2f} predicted Input {:2.2f} ".format(
    #  i, targetInput[i+1], predictedInput[i+1])

    if Y[-1] > 100000:
      print "predicted output diverged, terminate the process"
      predictedInput[(i + 1):] = 100000
      break

  predictedInput = (predictedInput * stdSeq) + meanSeq
  targetInput = (targetInput * stdSeq) + meanSeq
  trueData = (trueData * stdSeq) + meanSeq

  saveResultToFile(dataSet, predictedInput, 'Decay'+str(net.forgettingFactor)+'WAROSELM'+str(net.numHiddenNeurons))

  plt.figure()
  targetPlot,=plt.plot(targetInput,label='target',color='red')
  predictedPlot,=plt.plot(predictedInput,label='predicted',color='blue')
  plt.xlim([0,13500])
  plt.ylim([0, 30000])
  plt.ylabel('')
  plt.xlabel('')
  plt.legend(handles=[targetPlot, predictedPlot])

  #plt.draw()
  #plt.show()


  skipTrain = 500
  from plot import computeSquareDeviation
  squareDeviation = computeSquareDeviation(predictedInput, targetInput)
  squareDeviation[:skipTrain] = None
  nrmse = np.sqrt(np.nanmean(squareDeviation)) / np.nanstd(targetInput)
  print "NRMSE {}".format(nrmse)


  #raw_input()