import pandas as pd


class ExcelReader:
    def __init__(self, path):
        self.path = path

    def read_excel(self) -> pd.ExcelFile:
        """Reads the Excel file and returns a pd.ExcelFile object."""
        return pd.ExcelFile(self.path)

    def read_sheet(self, sheet_name: str) -> pd.DataFrame:
        """Reads the Excel file and returns a pd.DataFrame object."""
        return pd.read_excel(self.path, sheet_name=sheet_name)
    
    def read_sheets(self, sheet_names: list) -> dict:
        """Reads the Excel file and returns a dict of pd.DataFrame objects."""
        return pd.read_excel(self.path, sheet_name=sheet_names)
    
    def read_sheet_names(self) -> list:
        """Reads the Excel file and returns a list of sheet names."""
        return pd.ExcelFile(self.path).sheet_names