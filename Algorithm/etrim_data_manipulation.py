import datetime
import holidays
import pandas as pd


# process the temporal features
# the original time attributes on etrim are hard to program
def process_temporal(etrim):
    year, month, day, hour, minute, weekday, iso, timestamp, is_holiday = list(), list(), list(), list(), list(), list(), list(), list(), list()

    for index, row in etrim.iterrows():
        date = row['Date of Crash'].split(' ')[0]
        [accident_month, accident_day, accident_year] = date.split('/')
        year.append(2000 + int(accident_year))
        month.append(int(accident_month))
        day.append(int(accident_day))

        accident_time = row['Time of Crash']
        accident_hour = int(accident_time / 100)
        accident_minute = int(accident_time % 100)
        hour.append(accident_hour)
        minute.append(accident_minute)

        accident_datetime = datetime.datetime(2000 + int(accident_year), int(accident_month), int(accident_day),
                                              int(accident_hour), int(accident_minute))

        weekday.append(datetime.datetime.weekday(accident_datetime))
        iso.append(datetime.datetime.isoformat(accident_datetime))
        timestamp.append(datetime.datetime.timestamp(accident_datetime))

    return pd.DataFrame({'time': iso,
                         'year': year,
                         'month': month,
                         'day': day,
                         'hour': hour,
                         'minute': minute,
                         'weekday': weekday,
                         'timestamp': timestamp})


def derive_temporal(etrim):
    is_holiday = list()
    us_holiday = holidays.US()
    for index, row in etrim.iterrows():
        accident_year, accident_month, accident_day = row['year'], row['month'], row['day']
        accident_date = datetime.date(accident_year, accident_month, accident_day)
        if accident_date in us_holiday:
            is_holiday.append(1)
        else:
            is_holiday.append(0)
    return pd.DataFrame({'is_holiday': is_holiday})


# fetch weather data from darksky
# the original weather attributes on etrim are coarse
# have to create timestamp for each accident first
def get_darksky_feature(etrim, darksky):
    temperature, cloud_cover, dew_point, \
    humidity, precip_intensity, precip_probability, \
    uv_index, visibility, wind_speed = list(), list(), list(), \
                                       list(), list(), list(), \
                                       list(), list(), list()

    for index, row in etrim.iterrows():
        lat = row['GPS Coordinate Latitude']
        long = row['GPS Coordinate Longitude']
        timestamp = row['timestamp']

        time_machine_forecast = darksky.get_time_machine_forecast(lat, long, datetime.datetime.fromtimestamp(
            timestamp)).currently
        temperature.append(time_machine_forecast.temperature)
        cloud_cover.append(time_machine_forecast.cloud_cover)
        dew_point.append(time_machine_forecast.dew_point)
        humidity.append(time_machine_forecast.humidity)
        precip_intensity.append(time_machine_forecast.precip_intensity)
        precip_probability.append(time_machine_forecast.precip_probability)
        uv_index.append(time_machine_forecast.uv_index)
        visibility.append(time_machine_forecast.visibility)
        wind_speed.append(time_machine_forecast.wind_speed)

    darksky_dic = {'temperature': temperature,
                   'cloud_cover': cloud_cover,
                   'dew_point': dew_point,
                   'humidity': humidity,
                   'precip_intensity': precip_intensity,
                   'precip_probability': precip_probability,
                   'uv_index': uv_index,
                   'visibility': visibility,
                   'wind_speed': wind_speed}
    return pd.DataFrame(darksky_dic)
