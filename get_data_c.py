import requests, json
import sys
import pandas as pd
from tqdm import tqdm
import config
import time
import datetime 
import sky_places

def pause_API(request_start):
    request_sat = time.time()
    request_time_elapsed = request_sat - request_start
    time_sleep = 61-request_time_elapsed
    print("-----------")
    print("-----------")
    print(f"PAUSED for another {time_sleep} seconds")
    print("-----------")
    print("-----------")
    time.sleep(time_sleep)

class RequestFlights():
    def __init__(self):
        #self.origin_list = ['Madrid (ES)', 'Zurich (CH)']
        self.origin_list = ['Madrid', 'Zurich']
        self.origin_list_ids = []
        #self.destination_list = ['London (GB)']
        self.destination_list = ['London']
        self.destination_list_ids = []
        #self.date = '2021-03-01'
        self.date = 'anytime'
        self.num_flights = 3
        self.show_flight_info = False
        self.currency = 'EUR'

        self.params = {
            'origin_country' : 'ES',
            'currency': self.currency,
            'locale': 'en-US',
            'num_flights' : self.num_flights,
            'root_url': "https://skyscanner-skyscanner-flight-search-v1.p.rapidapi.com/apiservices/browsequotes/v1.0/",
            'show_flight_info': self.show_flight_info
            }

        columns = ['origin_sky_id', 'origin_iata_id', 'dest_sky_id', 'dest_iata_id', 'price', 'carrier', 'date']
        self.df_flights = pd.DataFrame(columns = columns)

        self.headers = {
            'x-rapidapi-key': config.api_key,
            'x-rapidapi-host': "skyscanner-skyscanner-flight-search-v1.p.rapidapi.com"
        }

    def __repr__(self):
        return(f'Origins: {self.origin_list} \n Destination(s): {self.destination_list}')
        
    @staticmethod
    def match_skyscanner(city_list):
        city_id = []
        table = pd.read_csv('Data/city_codes.csv')
        for city in city_list:
            city_id.append(list( table.loc[table['city_user'] == city, 'iata_sky_code'] ))
        city_id_list = [city for sub_city in city_id for city in sub_city]
        return city_id_list
    
    @staticmethod
    def get_places(place_list):
        sky_id = []
        for place in place_list:
            df = sky_places.main(place)
            sky_id.append(df['sky_id'].tolist())
        sky_id_list = [city for sub_city in sky_id for city in sub_city]

        return sky_id_list

    @staticmethod
    def assign_city_names(airport_iata_code):
        table = pd.read_csv('Data/city_codes.csv')
        city_name = table.loc[table['iata_code'] == airport_iata_code, 'city'].item()
        return city_name
    
    @staticmethod
    def str_to_date(x):
        return datetime.datetime.strptime(x, '%Y-%m-%d')
    
    @staticmethod
    def get_date_range(start, end):
        ''' start and end have to be in datetime format '''
        step = datetime.timedelta(days=1)
        date_range = []
        while start <= end:
            date_range.append( (start.date()).strftime('%Y-%m-%d') )
            start += step
        return date_range

    def get_user_params(self): 
        try:
            #self.origin_list_ids = self.match_skyscanner(self.origin_list)
            print('Requesting Origin Skyscanner IDs...')
            self.origin_list_ids = self.get_places(self.origin_list)
        except:
            print()
            print('The names provided don\'t match any cities or countries! Please try again: ')
        try:
            #self.destination_list_ids = self.match_skyscanner(self.destination_list)
            print('Requesting Destination Skyscanner IDs...')
            self.destination_list_ids = self.get_places(self.destination_list)
        except:
            print('The names provided don\'t match any cities or countries! Please try again: ')  
        
        # format dates to datetime, and get date ranges if two dates
        # check what API allows (some restrictions if one of dates is anytime)
        #if self.date_outbound != 'anytime':
            #self.date_outbound_1 = self.str_to_date(self.date_outbound_1)
            #if self.date_outbound_2 != 'anytime':
                #self.date_outbound_2 = self.str_to_date(self.date_outbound_2)
                #self.date_range_outbound = self.get_date_range(self.date_outbound_1, self.date_outbound_2)
        #else:
            #self.date_range_outbound = ['anytime']
        
        return self

    def print_flights(self, airport_origin, airport_dest, carrier, date, price):
        print("-----------")
        print(f"Journey: {airport_origin}  --> {airport_dest}")
        print(f"Date: {date}")
        print(f"Carrier: {carrier}")      
        print(f"Price: {price} {self.params['currency']}")
    
    def get_flights(self):
        count = 0
        request_start = time.time()
        airport_ID = {}
        carrier_ID = {}

        for origin in tqdm(self.origin_list_ids):
            for destination in tqdm(self.destination_list_ids, leave=False):
                try:
                    count += 1
                    if (count % 50 == 0) :
                        pause_API(request_start)
                        request_start = time.time() #reset time
                    
                    myurl = self.params['root_url'] + self.params['origin_country'] + "/" + self.params['currency'] + "/" + self.params['locale'] + "/"  + \
                        origin + "/" + destination + "/" + self.date
                    
                    r = requests.request("GET", myurl, headers=self.headers)
                    temp = json.loads(r.text)

                    for places in temp["Places"]:
                        airport_ID[places["PlaceId"]] = places["IataCode"] 
                
                    for carrier in temp["Carriers"]:
                        carrier_ID[carrier["CarrierId"]] = carrier["Name"]
                    
                    if "Quotes" in temp: 
                        for quotes in temp["Quotes"]:
                            # access data returned
                            origin_f = quotes["OutboundLeg"]["OriginId"]                     
                            carrier = quotes["OutboundLeg"]["CarrierIds"] #list of IDs,int
                            destination_f = quotes["OutboundLeg"]["DestinationId"]
                            price = quotes["MinPrice"]
                            date = (quotes["OutboundLeg"]["DepartureDate"].split("T"))[0]

                            # match to IDs
                            origin_iata_id = airport_ID[origin_f]
                            origin_sky_id = origin_iata_id + '-sky'
                            dest_iata_id = airport_ID[destination_f]
                            dest_sky_id = dest_iata_id + '-sky'
                            carrier_name = carrier_ID[carrier[0]]

                            self.df_flights = self.df_flights.append({'origin_sky_id': origin_sky_id, 'origin_iata_id': origin_iata_id, \
                                'dest_sky_id': dest_sky_id, 'dest_iata_id': dest_iata_id, 'price': price, 'carrier': carrier_name, \
                                    'date': date}, ignore_index=True)
                            
                            if self.show_flight_info:
                                self.print_flights(airport_ID[origin_f], airport_ID[destination_f], carrier_ID[carrier[0]], date, price)

                except:
                    continue

        try:
            self.df_flights['origin_city_name'] = self.df_flights.apply(lambda row: self.assign_city_names(row['origin_iata_id']), axis=1)
            self.df_flights['dest_city_name'] = self.df_flights.apply(lambda row: self.assign_city_names(row['dest_iata_id']), axis=1)
            
        except Exception:
            print('Origin City Not Found')
        
        return self


def main():
    print("Processing user-defined parameters...")
    print()
    Flights = RequestFlights()
    Flights.get_user_params()

    print()
    print("Requesting flight data...")
    Flights.get_flights()
    
    print()
    num = len(Flights.df_flights)
    print(f"Number of possible flights to be evaluated: {num}")
    print()

    print("Done!")

    print(Flights.df_flights)

    return Flights

if __name__ == '__main__':
    main()


                                

