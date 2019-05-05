import csv
import datetime
with open('/Users/wangshibao/SummerProjects/analytics-dashboard/myapp/CrimeHistory.csv','rU') as f:
        reader = csv.reader(f)
        header = reader.next()
        date_time = "20140501 00:00"
        date_time = datetime.datetime.strptime(date_time, "%Y%m%d %H:%M")
        print date_time

