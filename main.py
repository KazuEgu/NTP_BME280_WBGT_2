from machine import I2C,Pin
import bme280
import machine
from rw1063_lcd import RW1063LCD
#from esp8266_i2c_lcd import I2cLcd
import time
import env
import sys
import urequests as requests
import network
import socket
import struct
import ntptime

#led setting
led = machine.Pin("LED", machine.Pin.OUT)
led_red = Pin(15, Pin.OUT)
led_green = Pin(14, Pin.OUT)
led_red.value(0)
led_green.value(0)

#bme280 Setting
i2c = I2C(0,sda=Pin(16),scl=Pin(17),freq=400000)
bme = bme280.BME280(i2c=i2c)
print(bme.values)

#LCD i2C Setting
sda = machine.Pin(2)
scl = machine.Pin(3)
i2c_lcd = I2C(1,scl=scl,sda=sda,freq=400000)
lcd = RW1063LCD(i2c_lcd, addr=0x3F)
#lcd = I2cLcd(i2c_lcd, 0x3f, 4, 20)
lcd.clear()

#network　setting
class NET(object):
    #接続処理
    def __init__(self, ssid,passwd):
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            print('connecting to network...')
            wlan.connect(ssid, passwd)
            while not wlan.isconnected():
                time.sleep(1)
        print('network config:', wlan.ifconfig())

    #HTTPリクエスト
    def https_request(self,url):
        response = requests.get(url)
        http_buffer = response.text
        response.close()
        return http_buffer
    
    #NTPサーバから時刻取得
    def get_ntpdatetime(self,server):
        NTP_DELTA = 2208988800 #1900/1/1から1970/1/1までの秒数
        NTP_QUERY = bytearray(48)
        NTP_QUERY[0] = 0x1b
        addr = socket.getaddrinfo(server, 123)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        res = s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
        s.close()
        val = struct.unpack("!I", msg[40:44])[0]
        ntpsec = val - NTP_DELTA + 9*60*60
        nowtime = time.localtime()
        # 曜日を計算する
        days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        weekday = days_of_week[nowtime[6]]
        return nowtime, weekday
    
#ネットワーク接続
net = NET(env.WIFI_SSID, env.WIFI_PASS)

#Opening Message
wlan = network.WLAN(network.STA_IF)
ip_address = wlan.ifconfig()[0]
lcd.move_to(6,0)
lcd.putstr("Wellcome")
lcd.move_to(7,3)
lcd.putstr("JK1ALG")
lcd.move_to(3,2)
lcd.putstr(" {}".format(ip_address))
time.sleep(2)
lcd.clear()

#NTPサーバから時刻取得
ntptime.settime()
nowtime, weekday = net.get_ntpdatetime(env.NTP_SERVER)

# RTCに日時を設定
rtc = machine.RTC()
rtc.datetime((nowtime[0], nowtime[1], nowtime[2],nowtime[6],nowtime[3], nowtime[4], nowtime[5], 0))
print(rtc.datetime())

#counter reset
cnt = 0

#Temp&Humi&WBGT initial display
t, p, h = bme.read_compensated_data()
ti = round(t / 100, 1)  # 温度を小数点第一まで丸める
p = p // 256
pi = round(p / 100, 1)  # 気圧を小数点第一まで丸める
hi = round(h / 1024, 1)  # 湿度を小数点第一まで丸める
value = 0.725*ti+0.0368*hi+0.003664*hi*ti-3.246
value = round(value)

lcd.move_to(0, 2)
lcd.putstr("T:{:.1f}C P:{:.1f}hPa".format(ti, pi))
lcd.move_to(0, 3)
lcd.putstr("H:{:.1f}%".format(hi))
lcd.putstr(" WBGT:{}".format(value))

# Weekday names
weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

#TIME & DATE
while True:
 try:             
    #現在の時刻を取得
    nowtime=rtc.datetime()
    
    # UTCの時刻を取得
    utc_time = time.mktime((nowtime[0], nowtime[1], nowtime[2], nowtime[4], nowtime[5], nowtime[6], 0, 0))
    utc_struct_time = time.localtime(utc_time)
        
    # JSTの時刻を取得
    jst_time = time.mktime((nowtime[0], nowtime[1], nowtime[2], nowtime[4]+9, nowtime[5], nowtime[6], 0, 0))
    jst_struct_time = time.localtime(jst_time)
    
    # WBGTを計算&LED制御
    # WBGT Threshold
    NOTIFY_LEVEL1 = 28
    t, p, h = bme.read_compensated_data()
    ti = round(t / 100, 1)
    p = p // 256
    pi = round(p / 100, 1)
    hi = round(h / 1024, 1)
    value = 0.725*ti+0.0368*hi+0.003664*hi*ti-3.246
    value = round(value)
    print("WBGT: {}".format(value))
    
    #LCD表示
    lcd.move_to(0,0)
    lcd.putstr("Date:")
    lcd.move_to(5,0)
    lcd.putstr("{:4d}/{:02d}/{:02d}".format(jst_struct_time[0], jst_struct_time[1], jst_struct_time[2]))
    lcd.putstr("({})".format(weekdays[jst_struct_time[6]]))
    
    lcd.move_to(0, 1)
    lcd.putstr("{:02d}:{:02d}:{:02d}".format(jst_struct_time[3], jst_struct_time[4], jst_struct_time[5]))
    lcd.putstr(" <UTC>")
    lcd.putstr("{:02d}:{:02d}".format(utc_struct_time[3], utc_struct_time[4]))

    if (jst_struct_time[5])%30 == 0:
        t, p, h = bme.read_compensated_data()
        ti = round(t / 100, 1)
        p = p // 256
        pi = round(p / 100, 1)
        hi = round(h / 1024, 1)
        lcd.move_to(0, 2)
        lcd.putstr("T:{:.1f}C P:{:.1f}hPa".format(ti, pi))
        lcd.move_to(0, 3)
        lcd.putstr("H:{:.1f}%".format(hi))
        lcd.putstr(" WBGT:{}".format(value))
        #RED/Green LED
        led_red.value(0)
        led_green.value(0)
        if value >= NOTIFY_LEVEL1:
            led_red.value(1)
        if value < NOTIFY_LEVEL1:
            led_green.value(1)
               
    led.value(1)
    time.sleep(0.2)
    led.value(0)
    
    if (cnt) == 100:
        cnt = 0
        
    print(cnt)
    cnt += 1
    
 except KeyboardInterrupt:
     sys.exit()
     
