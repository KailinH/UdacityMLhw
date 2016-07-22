#!/usr/bin/python

""" 
    Starter code for exploring the Enron dataset (emails + finances);
    loads up the dataset (pickled dict of dicts).

    The dataset has the form:
    enron_data["LASTNAME FIRSTNAME MIDDLEINITIAL"] = { features_dict }

    {features_dict} is a dictionary of features associated with that person.
    You should explore features_dict as part of the mini-project,
    but here's an example to get you started:

    enron_data["SKILLING JEFFREY K"]["bonus"] = 5600000
    
"""

import pickle

enron_data = pickle.load(open("../final_project/final_project_dataset.pkl", "r"))
########my part#############
print ("everybody in dataset: ",enron_data.keys())#or list(enron_data)
print (enron_data['METTS MARK'])
print (enron_data['LAY KENNETH L'])
count = 0
for k in enron_data.keys():
    if enron_data[k]["poi"]==1:
        count +=1
print (count)
poi_num = 0
poi = open('/Users/kailinh/ud120-projects/final_project/poi_names.txt', 'r')##read in as a file
for line in poi:
    poi_num += 1
print(poi_num)
print(poi.read())
with open('/Users/kailinh/ud120-projects/final_project/poi_names.txt') as f:
    content = f.readlines()
#print (len(content),content)
print (enron_data["PRENTICE JAMES"]["total_stock_value"])
print (enron_data["COLWELL WESLEY"]["from_this_person_to_poi"])
print (enron_data["SKILLING JEFFREY K"]["exercised_stock_options"])
print (enron_data["LAY KENNETH L"]["total_payments"],enron_data["SKILLING JEFFREY K"]["total_payments"],enron_data["FASTOW ANDREW S"]["total_payments"])
salary_quan = 0
email_quan = 0
for k in enron_data.keys():
    if enron_data[k]["salary"]!='NaN':
        salary_quan +=1
for k in enron_data.keys():
    if enron_data[k]["email_address"]!='NaN':
        email_quan +=1
salary_quan1 = [k for k in enron_data.keys()if enron_data[k]["salary"]!='NaN']#list comprehension better
print (salary_quan,email_quan,len(salary_quan1))
no_payment_poi = [k for k in enron_data.keys()if (enron_data[k]["total_payments"]=='NaN')&(enron_data[k]["poi"]=='True')]
print (no_payment_poi)##every poi has total_payment info
##how to sort it with regard to salary or query it easily##
print ("salary in order: ",sorted(enron_data.values(),key=lambda person: person["salary"]))
############################################

