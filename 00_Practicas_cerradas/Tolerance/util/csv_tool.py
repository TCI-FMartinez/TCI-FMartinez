import pandas as pd
from os import path, sep
#import pyperclip

def csv_to_dict(filename):
    df = pd.read_csv(filename)
    row_names = df.iloc[:,0].tolist()
    list_dict = {}
    for n in range(len(row_names)): 
        list_dict[row_names[n]] = df.iloc[n, 1:].tolist()
    return list_dict

holes = csv_to_dict(f'util{sep}iso_holes.csv')
shafts = csv_to_dict(f'util{sep}iso_shafts.csv')

#pyperclip.copy(str(shafts))
if __name__ == "__main__":
    print("Holes:")
    print(holes)
    print("Shafts:")
    print(shafts)