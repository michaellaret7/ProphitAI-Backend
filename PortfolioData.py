from ib_insync import IB, Stock, util, ContFuture
from datetime import datetime
from ib_insync import *

def connect_to_ib():
    ib = IB()
    if ib.isConnected():
        ib.disconnect()

    connected = False

    for port in [4002, 7497]:
        for clientId in range(7):  # Try client IDs from 0 to 6
            try:
                ib.connect('127.0.0.1', port, clientId=clientId)
                connected = True
                print(f"🌐 Connected successfully on port {port} with clientId {clientId}")
                break  # Break out of the clientId loop
            except Exception as e:
                print(f"🚨 Failed to connect on port {port} with clientId {clientId}: {e}")
                pass
        
        if connected:
            break  # Break out of the port loop if we're connected
    
    if not connected:
        print("⛔ Could not connect to IB on any port with any clientId")
        return None

    return ib


