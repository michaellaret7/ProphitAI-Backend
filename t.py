from app.brokers.alpaca_broker import ProphitBroker

broker = ProphitBroker(sandbox=True)

user_data = {
    "first_name": "John",
    "last_name": "Doe",
    "email": "johndoe@example.com",
    "phone": "555-123-4567",
    "address": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip": "10001",
    "dob": "1990-01-15",
    "ssn": "482-37-9154",
    "funding_source": "employment_income",
}

account = broker.create_account(user_data)
print(account)
