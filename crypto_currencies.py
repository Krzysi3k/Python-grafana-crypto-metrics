from bs4 import BeautifulSoup
from urllib import request
from urllib.request import Request
import time
import requests
import re
import sys
import logging


class CryptoReader:
    def __init__(self, convert_toPLN=False):
        self.convert_toPLN = convert_toPLN
        self.DB_NAME = 'currencies'
        self.MEASUREMENT = 'CryptoValue'
        self.CURRENCY_LST = ['BTC', 'ETH', 'BCH', 'LTC', 'IOTA', 'ZEC']
        LOG_FORMAT = "%(levelname)s %(asctime)s %(message)s"
        logging.basicConfig(filename = 'C:\\Temp\\big_log.log',
                            level = logging.INFO,
                            format = LOG_FORMAT)
        self.logger = logging.getLogger()

    def read_prices(self):
        url = "https://www.investing.com/crypto/currencies"
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = request.urlopen(req)
        soup = BeautifulSoup(response.read(), 'html.parser')
        table = soup.find(id='fullColumn')
        table_body = table.find('tbody')
        rows = table_body.findAll('tr')
        currency_dict = {}

        for currency in self.CURRENCY_LST:
            cur_pattern = 'title="%s"' % currency
            for row in rows:
                if re.findall(cur_pattern, str(row)):
                    curr_value = (row.find(class_='price js-currency-price').text).replace(',','')
                    curr_rounded = round(float(curr_value),2)
                    currency_dict.update({currency:curr_rounded})
                    break

        if self.convert_toPLN == True:
            pln_url = 'https://stooq.pl/q/?s=usdpln'
            pln_req = Request(pln_url, headers={'User-Agent': 'Mozilla/5.0'})
            pln_html = request.urlopen(pln_req)
            pln_reader = BeautifulSoup(pln_html.read(), 'html.parser')
            pln_value = pln_reader.find(id='aq_usdpln_c5').text
            for key, value in currency_dict.items():
                currency_dict[key] = round(float(value) * float(pln_value),2)

        return currency_dict

    def post_to_influxDB(self, db_name, measurement, curr_table):
        timestamp = time.strftime('%H:%M:%S', time.localtime(time.time()))
        uri = 'http://localhost:8086/write?db=%s' % db_name
        try:
            for key, value in curr_table.items():
                body = '%s,currency=%s value=%s' % (measurement, key, value)
                requests.post(uri, data=body)
            self.logger.info(str(curr_table))
            print(timestamp + ' ' + str(curr_table))
        except Exception as e:
            print(timestamp + ' ' + 'cannot post to influxdb', str(e))
            self.logger.error(str(e))
            # this log is optional:
            with open("C:\\Temp\\error_log.log", "a") as err_log:
                err_log.write(str(e) + "\n")
            err_log.close()

    def main(self):
        minutes = 2
        print('started posting data to InfluxDB and Grafana...')
        while True:
            curr_table = self.read_prices()
            self.post_to_influxDB(self.DB_NAME, self.MEASUREMENT, curr_table)
            time.sleep(60 * minutes)



if __name__ == '__main__':
    if len(sys.argv) == 2:
        if sys.argv[1] == 'pln':
            r = CryptoReader(convert_toPLN=True)
            r.main()
    else:
        r = CryptoReader()
        r.main()