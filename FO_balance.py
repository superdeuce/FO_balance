"""
for reading balance digits during a FO measurement
written by Chih-Hao 2017/06/15
"""
import pandas as pd
import time
import re    
import serial
import os
#%% Input parameters
file_name = '20170615_3.5wt-saline_DIwater_20mm'
exp_length_min = 60*10  #total measurement in minutes
period_min = 1          #recording intervals in minutes
#exp_mode = 'PRO mode'   #active layer faced to draw: PRO mode
exp_mode = 'FO mode'    #active layer faced to feed: FO mode
draw_sol = '3.5wt% saline'
init_draw_weight = 50   #g
feed_sol = 'DI water'
init_feed_weight = 200  #g
flow_rate = 20          #volumetric flow rate, ml/min
CFV = flow_rate/(0.23*3.92*60) #cross flow velocity, cm/s
memo = 'no steel shim, no feed spacer'
#%%Show available ports (find ATEN USB to Serial Bridge)
import serial.tools.list_ports as port_list
ports = list(port_list.comports())
for p in ports: print(p)

#Global Variables
ser = 0
#Function to Initialize the Serial Port
def init_serial():
    COMNUM = 4          #Enter Your COM Port Number Here.
    global ser          #Must be declared in Each Function
    ser = serial.Serial()
    ser.baudrate = 9600
    ser.port = "COM{}".format(COMNUM)   
    #ser.port = '/dev/ttyUSB0' #If Using Linux
    ser.timeout = 10    #Specify the TimeOut in seconds, so that SerialPort doesn't hangs
    ser.open()          #Opens SerialPort   
    if ser.isOpen():    # print port open or closed
        print('Open: ' + ser.portstr)      
  
#%% Starting measurement (animal mode,averaged weight in 5 sec)
init_serial()  #initiallization
print('initialize the experiment for ' + str(exp_length_min) + ' minutes in '+ exp_mode)
#Experimental condition
df0 = pd.DataFrame({'exp info':['draw','feed','mode','exp length(min)','exp period(min)','init draw(g)','init feed(g)','flow rate(ml/min)','cross flow velocity(cm/s)','memo'],
                   'exp_info':[draw_sol, feed_sol, exp_mode, exp_length_min, period_min, init_draw_weight, init_feed_weight, flow_rate,CFV, memo]}) 
                        
df = pd.DataFrame(columns = ['time','elapsed time(min)','weight(g)',
                             'weight change(acc.)','flux(LMH,acc.)',
                             'weight change(per min)', 'flux(LMH,per min)'])  #creating a dataframe of result
                             
elapsed_time = 0
mem_area = 42               #membrane area, cm^2
weight_tol = 1*period_min   #tolerance of weight change per minute, g
for i in range(int(exp_length_min/period_min)):  
    time_now = time.ctime()    
    ser.write('E'.encode())             #press "enter"
    time.sleep(6)
    ser.write('E'.encode())             #print the result
    no_use_time = ser.readline()        #read time (5 sec) for averaging, no use, type in byte
    read_weight = ser.readline()        #read averaged weight in animal mode, type in byte
    avg_weight = float(re.findall("\d+\.\d+", str(read_weight))[0])    #convert read-weight into floats
    
    ser.write('O'.encode())             #end reading avg weight for the next measurement
    
    if i == 0:
        weight_init = avg_weight
        weight_previous = avg_weight
        df.loc[i,['time','elapsed time(min)','weight(g)']] = [time_now ,elapsed_time, avg_weight]
        print("elapsed {} min, weight {} g".format(elapsed_time,avg_weight))
    elif (i < 10) & (avg_weight > weight_previous): #if weight increased, recounting time
        weight_init = avg_weight
        weight_previous = avg_weight
        elapsed_time = 0
        df.loc[i,['time','elapsed time(min)','weight(g)']] = [time_now ,elapsed_time, avg_weight]
        print("elapsed {} min, weight {} g".format(elapsed_time,avg_weight))
    elif (i < 10) & ((weight_previous-avg_weight) > weight_tol): #if weight decreased too rapid, recounting time
        weight_init = avg_weight
        weight_previous = avg_weight
        elapsed_time = 0
        df.loc[i,['time','elapsed time(min)','weight(g)']] = [time_now ,elapsed_time, avg_weight]
        print("elapsed {} min, weight {} g".format(elapsed_time,avg_weight))
    else:
        weight_change_accu = weight_init - avg_weight
        weight_change_period = weight_previous - avg_weight
        flux_accu = (weight_change_accu/1000)/((mem_area/10000)*(elapsed_time/60))     
        flux_period = (weight_change_period/1000)/((mem_area/10000)*(period_min/60))
        df.loc[i] = [time.ctime() ,elapsed_time, avg_weight, weight_change_accu,
                    flux_accu, weight_change_period, flux_period]
        print("elapsed {} min, weight {} g, flux(accu): {} LMH, flux(per): {} LMH".format(elapsed_time,avg_weight,round(flux_accu,2),round(flux_period,2)))
        weight_previous = avg_weight # for the use of next loop

    time.sleep(period_min*60-6)     #wait a period(sec) for next measurement
    elapsed_time += period_min
print("experiment finished")
#Save file        
df = pd.concat([df0,df], axis=1)    #conbine exp description and data  
cwd = os.getcwd()
df.to_csv(os.path.join(cwd,'experimental data',file_name + '.csv'), index=False)