import json
import os

class CurrencyManager:
    def __init__(self, json_file):
        self.json_file = json_file
        self.load_data()

    def load_data(self):
        if os.path.exists(self.json_file):
            with open(self.json_file, 'r') as f:
                self.user_currencies = json.load(f)
        else:
            self.user_currencies = {}

    def save_data(self):
        with open(self.json_file, 'w') as f:
            json.dump(self.user_currencies, f, indent=4)

    def get_currency(self, user_id):
        return self.user_currencies.get(str(user_id), 0)

    def update_currency(self, user_id, amount):
        if str(user_id) in self.user_currencies:
            self.user_currencies[str(user_id)] += amount
        else:
            self.user_currencies[str(user_id)] = amount
        self.save_data()
