from ib_insync import IB
import atexit

# Global IB instance
ib = None

def connect_to_ib():
    """
    Connect to Interactive Brokers TWS or Gateway.
    Returns a singleton IB instance, creating a new connection only if needed.
    
    Returns:
        IB: Connected IB instance or None if connection failed
    """
    global ib
    
    # If already connected, return the existing connection
    if ib is not None and ib.isConnected():
        return ib
    
    ib = IB()
    if ib.isConnected():
        ib.disconnect()

    connected = False
    ports = [7497, 4002]

    for clientId in range(8):  # Try client IDs from 0 to 7
        for port in ports:
            try:
                ib.connect('127.0.0.1', port, clientId=clientId)
                connected = True
                print(f"🌐 Connected successfully on port {port} with clientId {clientId}")
                break  # Break out of the port loop
            except Exception as e:
                print(f"🚨 Failed to connect on port {port} with clientId {clientId}: {e}")
                pass
        
        if connected:
            break  # Break out of the clientId loop if we're connected
    
    if not connected:
        print("⛔ Could not connect to IB on any port with any clientId")
        return None

    # Register the disconnect function to run on exit
    atexit.register(disconnect_from_ib)
    
    return ib

def disconnect_from_ib():
    """
    Disconnect from Interactive Brokers.
    Safe to call even if not connected.
    """
    global ib
    if ib is not None and ib.isConnected():
        print("📴 Disconnecting from IB")
        ib.disconnect()

def get_ib():
    """
    Get the current IB instance, connecting if necessary.
    
    Returns:
        IB: Connected IB instance or None if connection failed
    """
    global ib
    if ib is None or not ib.isConnected():
        return connect_to_ib()
    return ib 