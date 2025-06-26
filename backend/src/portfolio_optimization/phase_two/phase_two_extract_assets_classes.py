import json

class PhaseTwoExtractAssetClasses:
    def __init__(self, phase_one_data):
        self.asset_classes = phase_one_data
    
    def get_asset_classes(self):
        portfolio = self.asset_classes.get("portfolio", [])
        asset_classes = [item.get("asset_class") for item in portfolio]
        return [ac for ac in asset_classes if ac]
    
    def get_asset_class_allocations(self):
        portfolio = self.asset_classes.get("portfolio", [])
        asset_class_allocations = {item.get("asset_class"): item.get("allocation") for item in portfolio}
        return asset_class_allocations