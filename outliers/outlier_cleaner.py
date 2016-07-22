#!/usr/bin/python


def outlierCleaner(predictions, ages, net_worths):
    """
        Clean away the 10% of points that have the largest
        residual errors (difference between the prediction
        and the actual net worth).

        Return a list of tuples named cleaned_data where 
        each tuple is of the form (age, net_worth, error).
    """
    
    cleaned_data = []

    ### your code goes here
    data = []
    for i in range(len(ages)):
        data.append( [ages[i],net_worths[i],(net_worths[i]-predictions[i])])
        data.sort(key=lambda x: x[2])
        cleaned_data = data[9:]
   
    return cleaned_data

