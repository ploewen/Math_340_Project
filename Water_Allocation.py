#Import Data Files
import numpy as np
import scipy.linalg as la
import pulp
from pulp import *
import pandas as pd
import plotly.express as px

animalDf = pd.read_csv("Animal_Water.csv")
plantDf = pd.read_csv("Plant_Water.csv")
df = pd.read_csv("Farms.csv")
RevExp = pd.read_csv("Revenue_Expense.csv")



df = df[(df['Farm_Area_Size'] != 'All') & 
        (df['Description'] != 'All') & 
        (df['Gross_Farm_Receipt_Category'] != 'Total ')].iloc[:,[1,3,4,5]].reset_index(drop = True)



df = df.replace(pd.unique(df['Gross_Farm_Receipt_Category']),
                [2500, 4999, 9999,24999,49999,99999,249999,499999,750000])
df = df.replace(pd.unique(df['Farm_Area_Size']),
                [1, 5, 11]).rename(columns = {'Description':'Farm_Type'})


df = df[(df['Farm_Type'] != 'Dairy cattle and milk production') & 
        (df['Farm_Type'] != 'Beef cattle ranching and farming, including feedlots') & 
        (df['Farm_Type'] != 'Hog and pig farming') &
        (df['Farm_Type'] != 'Poultry and egg production') &
        (df['Farm_Type'] != 'Sheep and goat farming') &
        (df['Farm_Type'] != 'Other animal production')].reset_index()


prct = pd.DataFrame().assign(Farm_Type = RevExp['Farm_Type'], cutoffPrct = RevExp['Average_expense']/RevExp['Average_revenue'])
df = pd.DataFrame.merge(df, prct, on = 'Farm_Type')
df['cutoff'] = df['Gross_Farm_Receipt_Category'] * df['cutoffPrct']/12


farms = pd.DataFrame().assign(Farm_Type = df['Farm_Type'], 
                              Gross_Farm_Receipt_Category = df['Gross_Farm_Receipt_Category'], 
                              Farm_Area_Size = df['Farm_Area_Size'],
                              Number_of_Farms = df['Number_of_Farms'])
farms = farms.loc[farms.index.repeat(farms.Number_of_Farms)].drop('Number_of_Farms', axis = 1)

grp_df = farms.groupby(['Farm_Type', 'Gross_Farm_Receipt_Category']).count()

wtr_df = pd.DataFrame.merge(farms, plantDf, on = ['Farm_Type'], how = 'left')
wtr_df['Farm_Area_Size'] = wtr_df['Farm_Area_Size']*4046.86
wtr_df['Avg_Req_m'] = wtr_df['Avg_Req_mm']/12000
wtr_df['Req_Water_m^3'] = wtr_df['Avg_Req_m'] * wtr_df['Farm_Area_Size']
wtr_df['Req_Water_Gal'] = wtr_df['Req_Water_m^3'] * 264.172

wtr_df = pd.DataFrame.merge(wtr_df, prct, on = 'Farm_Type')
wtr_df['Min_Water_Gal'] = wtr_df['Req_Water_Gal'] * wtr_df['cutoffPrct']
wtr_df['Cutoff_Price'] = wtr_df['Gross_Farm_Receipt_Category'] * wtr_df['cutoffPrct']/12
wtr_df['Gross_Farm_Receipt_Category'] = wtr_df['Gross_Farm_Receipt_Category']/12

wtr_df_sum = wtr_df.drop(columns = ['Avg_Req_mm', 'Avg_Req_m', 'Req_Water_m^3', 'cutoffPrct']).groupby('Farm_Type').sum().reset_index()
wtr_df_sum


animalReq = 0
for i in range(len(animalDf)):
    animalReq = animalReq + int(animalDf['Total Gallons Per Month'][i])

availableH2O = 15850323141 - animalReq

farmRevDic = {wtr_df_sum['Farm_Type'][i]: 
                    {wtr_df_sum['Gross_Farm_Receipt_Category'][i]}
              for i in range(len(wtr_df_sum)) }

minRevDic = {wtr_df_sum['Farm_Type'][i]: 
                    {wtr_df_sum['Cutoff_Price'][i]}
            for i in range(len(wtr_df_sum))}

farmWaterDic = {wtr_df_sum['Farm_Type'][i]: 
                        {wtr_df_sum['Req_Water_Gal'][i]} 
                for i in range(len(wtr_df_sum)) } 


minWaterDic = {wtr_df_sum['Farm_Type'][i]: 
                        {wtr_df_sum['Min_Water_Gal'][i]}
               for i in range(len(wtr_df_sum)) }

q = [i for i in pd.unique(wtr_df_sum['Farm_Type'])]


maxRev = LpProblem("Revenue_Maximization", LpMaximize)

qvars = LpVariable.dicts('q', q, 0)

maxRev += lpSum(qvars[i]* list(farmRevDic[i])[0]/list(farmWaterDic[i])[0]for i in q)
maxRev += lpSum(qvars[i] for i in q) <= availableH2O

for i in q:
    maxRev+= qvars[i] >= minWaterDic[i]
maxRev

maxRev.solve()
LpStatus[maxRev.status]

for variable in maxRev.variables():
        print(variable.name, "=", variable.varValue)
print("Optimal revenue is ", value(maxRev.objective), "$")