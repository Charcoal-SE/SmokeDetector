import csv
import sys

txt_file = r"bad_keywords.txt"
csv_file = r"bad_keywords.csv"

in_txt = open(txt_file, "r")
out_csv = csv.writer(open(csv_file, 'wb'))

file_string = in_txt.read()

file_list = file_string.split('\n')

for row in ec_file_list:
    out_csv.writerow(row)