
temp = -10
wind = 6
feels_like = lambda w, t: int(13.12+(0.615*float(t))-(11.37*(float(w)*3.6)**0.16)+(0.3965*float(t))*((float(w)*3.6)**0.16))

print (feels_like(wind, temp), "'C" )