import numpy as np
import MySQLdb
import threading
from enum import Enum
from scipy.special import expit, logit
import sched, time

class Mode(Enum):
    Training = 0
    Testing = 1
    
class CalculationCycle(Enum):
    TenMinutes = 6000
    ThirtyMinutes = 18000
    OneHour = 36000
    
class TrainingCycle(Enum):
    Day = 0
    Week = 1
    Month = 2

class Setting(object):
    
    def __init__(self):
        self.mode = Mode.Training
        self.calCycle = CalculationCycle.OneHour
        self.trainCycle = TrainingCycle.Day
        
    def changeMode(self, mode):
        self.mode = mode
        
    def changeCalCycle(self, calculationCycle):
        self.calCycle = calculationCycle
        
    def changeTrainCycle(self, trainingCycle):
        self.trainCycle = trainingCycle

def printMainMenu():
    print("===============================")
    print("This is Home Automation System.")
    print("=============menu==============")
    print("1. Setting")
    print("2. Train")
    print("3. Predict")
    print("4. Exit")
    print("===============================")

def printSettingMenu():
    print("===============================")
    print("===========Setting=============")
    print("=============menu==============")
    print("1. Change Calculation Cycle")
    print("2. Change Training Cycle")
    print("3. Return to Main Menu")
    print("===============================")

def printChangeCalCycleMenu():
    print("===============================")
    print("====Change Calculation Cycle===")
    print("=============menu==============")
    print("1. 10 Minutes")
    print("2. 30 Minutes")
    print("3. 1 Hour")
    print("4. Return to Main Menu")
    print("===============================")
    
def printChangeTrainCycleMenu():
    print("===============================")
    print("=====Change Training Cycle=====")
    print("=============menu==============")
    print("1. 1 Day")
    print("2. 1 Week")
    print("3. 1 Month")
    print("4. Return to Main Menu")
    print("===============================")



class Scheduler(object):
    
    def __init__(self):
        self.NN = Neural_Network()
        self.setting = Setting()
        
    def predict(self, sc):
        #threading.Timer(1, Scheduler.predict).start()
        recentRecord = self.getRecentRecord()
        if recentRecord.size == 0:
            print("There is not enough record")
        else:
            tday = recentRecord['f0']
            timeInMinute = recentRecord['f1']
            humidity = recentRecord['f2']
            recentRecordFloat = np.array((tday, timeInMinute, humidity), dtype=float)
            recentRecordFloat = recentRecordFloat.T
            print("Final prediction: \n" + str(self.NN.forwardPass(recentRecordFloat)*50))
            #s.enter(self.setting.calCycle.value, 1, Schd.predict, (sc,))
            s.enter(1, 1, Schd.predict, (sc,))
            return self.NN.forwardPass(recentRecordFloat)
    
    def getRecentRecord(self):
        conn = MySQLdb.connect(host= "localhost",user= "monitor",passwd="",db="temps")
        curs = conn.cursor()
        numrows = curs.execute("SELECT tday, timeInMinute, humidity FROM TrainTestData ORDER BY tdate DESC LIMIT 1") #TrainingCycle, where date > now.day-1 (day/week)
        record = np.fromiter(curs.fetchall(), count=numrows, dtype=('i4, i4, i4'))
        return record
    
    def getDayRecord(self):
        conn = MySQLdb.connect(host= "localhost",user= "monitor",passwd="",db="temps")
        curs = conn.cursor()
        numrows = curs.execute("SELECT tday, timeInMinute, humidity, temperature FROM TrainTestData WHERE tdate >= NOW() - INTERVAL 1 DAY") #TrainingCycle, where date > now.day-1 (day/week)
        #numrows = curs.execute("SELECT tday, timeInMinute, humidity, temperature FROM TrainTestData") #TrainingCycle, where date > now.day-1 (day/week)
        record = np.fromiter(curs.fetchall(), count=numrows, dtype=('i4, i4, i4, i4'))
        return record
    
    def getWeekRecord(self):
        conn = MySQLdb.connect(host= "localhost",user= "monitor",passwd="",db="temps")
        curs = conn.cursor()
        numrows = curs.execute("SELECT tday, timeInMinute, humidity, temperature FROM TrainTestData WHERE tdate >= NOW() - INTERVAL 1 WEEK") #TrainingCycle, where date > now.day-1 (day/week)
        record = np.fromiter(curs.fetchall(), count=numrows, dtype=('i4, i4, i4, i4'))
        return record
    
    def getMonthRecord(self):
        conn = MySQLdb.connect(host= "localhost",user= "monitor",passwd="",db="temps")
        curs = conn.cursor()
        numrows = curs.execute("SELECT tday, timeInMinute, humidity, temperature FROM TrainTestData WHERE tdate >= NOW() - INTERVAL 1 MONTH") #TrainingCycle, where date > now.day-1 (day/week)
        record = np.fromiter(curs.fetchall(), count=numrows, dtype=('i4, i4, i4, i4'))
        return record
    
    def learn(self):
        if self.setting.trainCycle == TrainingCycle.Day:
            print("TrainingCycle is 1 day")
            record = self.getDayRecord()
        elif self.setting.trainCycle == TrainingCycle.Week:
            print("TrainingCycle is 1 week")
            record = self.getWeekRecord()
        elif self.setting.trainCycle == TrainingCycle.Month:
            print("TrainingCycle is 1 month")
            record = self.getMonthRecord()
        if record.size == 0:
            print("There is not enough record")
        else:
            tday = record['f0']
            timeInMinute = record['f1']
            humidity = record['f2']
            temperature = record['f3']
            inputPredict = np.array((tday, timeInMinute, humidity), dtype=float)
            inputPredict = inputPredict.T
            tempArray = np.array(temperature, dtype=float)
            actualOutput = np.reshape(tempArray, (-1, 1))
            inputPredict = inputPredict/np.amax(inputPredict, axis=0)
            actualOutput = actualOutput/50
            
            for i in range(16):
                #print ("Input: \n" + str(inputPredict) )
                #print ("Actual Output: \n" + str(actualOutput) )
                #print ("Predicted Output: \n" + str(self.NN.forwardPass(inputPredict)))
                print ("MSE: " + str(np.mean(np.square(actualOutput - self.NN.forwardPass(inputPredict)))))
                #print ("\n")
                print("iteration: " + str(i) + " time(s)")
                self.NN.train(inputPredict, actualOutput)
            print("Learning Complete! \n")
        #return NN


class Neural_Network(object):
    def __init__(self):
        self.sizeInput = 3
        self.sizeOutput = 1
        self.sizeHidden = 3
        self.weight1 = np.random.randn(self.sizeInput, self.sizeHidden)
        self.weight2 = np.random.randn(self.sizeHidden, self.sizeOutput)

    def forwardPass(self, inputPredict):
        self.product1 = np.dot(inputPredict, self.weight1)
        self.product2 = self.sigmoid(self.product1)
        self.product3 = np.dot(self.product2, self.weight2)
        predictedOutput = self.sigmoid(self.product3)
        return predictedOutput 

    def sigmoid(self, s):
        return expit(s)
        #return 1/(1+np.exp(-s))

    def sigmoidPrime(self, s):
        return s * (1 - s)

    def backward(self, inputPredict, actualOutput, predictedOutput):
        self.o_error = actualOutput - predictedOutput
        self.o_delta = self.o_error*self.sigmoidPrime(predictedOutput)
        self.z2_error = self.o_delta.dot(self.weight2.T)
        self.z2_delta = self.z2_error*self.sigmoidPrime(self.product2)
        self.weight1 += inputPredict.T.dot(self.z2_delta)
        self.weight2 += self.product2.T.dot(self.o_delta)

    def train (self, inputPredict, actualOutput):
        predictedOutput = self.forwardPass(inputPredict)
        self.backward(inputPredict, actualOutput, predictedOutput)



Schd = Scheduler()
s = sched.scheduler(time.time, time.sleep)
loop=True      
  
while loop:
    printMainMenu()
    choice = input("Please Select Action : ")
    print("===============================\n")
     
    if choice==1:     
        printSettingMenu()
        choiceSetting = input("Please Select Action : ")
        print("===============================\n")
        if choiceSetting==1:
            printChangeCalCycleMenu()
            choiceCalCycle = input("Please Select Action : ")
            print("===============================\n")
            if choiceCalCycle==1:
                Schd.setting.changeCalCycle(CalculationCycle.TenMinutes)
                print("Calculation Cycle has been changed to 10 Minutes")
            elif choiceCalCycle==2:
                Schd.setting.changeCalCycle(CalculationCycle.ThirtyMinutes)
                print("Calculation Cycle has been changed to 30 Minutes")
            elif choiceCalCycle==3:
                Schd.setting.changeCalCycle(CalculationCycle.OneHour)
                print("Calculation Cycle has been changed to 1 Hour")
            elif choiceCalCycle==4:
                print("Back to Main Menu")
            else:
                raw_input("Wrong option selection. Enter any key to try again..")
        elif choiceSetting==2:
            printChangeTrainCycleMenu()
            choiceTrainCycle = input("Please Select Action : ")
            print("===============================\n")
            if choiceTrainCycle==1:
                Schd.setting.changeTrainCycle(TrainingCycle.Day)
                print("Training Cycle has been changed to 1 Day")
            elif choiceTrainCycle==2:
                Schd.setting.changeTrainCycle(TrainingCycle.Week)
                print("Training Cycle has been changed to 1 Week")
            elif choiceTrainCycle==3:
                Schd.setting.changeTrainCycle(TrainingCycle.Month)
                print("Training Cycle has been changed to 1 Month")
            elif choiceTrainCycle==4:
                print("Back to Main Menu")
            else:
                raw_input("Wrong option selection. Enter any key to try again..")
        elif choiceSetting==3:
            print("Back to Main Menu")
        else:
            raw_input("Wrong option selection. Enter any key to try again..")
    elif choice==2:
        print("Training Mode Begin...")
        Schd.learn()
    elif choice==3:
        print("Predict Mode Begin...")
        #Schd.predict()
        #s.enter(Schd.setting.calCycle.value, 1, Schd.predict, (s,))
        s.enter(1, 1, Schd.predict, (s,))
        s.run()
    elif choice==4:
        print("Exit, Thank you.")
        loop=False
    else:
        raw_input("Wrong option selection. Enter any key to try again..")
        print("===============================\n")

