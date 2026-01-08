### Dates ###

# https://docs.python.org/es/3/library/datetime.html

from datetime import datetime, UTC
#from datetime import time
from datetime import date
#from datetime import timedelta


ahora = datetime.now()

ahora_hora = f"{ahora.hour}:{ahora.minute}:{ahora.second}"
ahora_fecha = f"{ahora.day}-{ahora.month}-{ahora.year}"
timestamp = str(f"{ahora_fecha} {ahora_hora}")

#print(ahora_hora)
#print(ahora_fecha)
#print(timestamp)
