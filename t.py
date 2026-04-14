from pandas import DataFrame

df = DataFrame({
    "a": [1, 2, 3],
    "b": [4, 5, 6],
})

df_2 = DataFrame({
    "month": [1, 2, 3],
    "year": [2020, 2020, 2020],
    "value": [10, 20, 30],
})

df.attrs["df_2"] = df_2

df.attrs.get("df_2")
print(df.attrs.get("df_2"))

print(df)

