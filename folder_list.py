import os

# Path to the folder
folder_path = "rasters_by_date"

# List items in the folder
if os.path.exists(folder_path):
    items = sorted(os.listdir(folder_path))  # Sort items to ensure order
    variables = {}
    all_dates = set()  # Use a set to store unique dates

    # Group files by variable name
    for item in items:
        if item.endswith(".tif"):
            var_name = "_".join(item.split("_")[:-1])  # Extract variable name
            date = item.split("_")[-1].replace(".tif", "")  # Extract date
            all_dates.add(date)  # Add the date to the set
            if var_name not in variables:
                variables[var_name] = []
            variables[var_name].append(item)

    # Convert the set of dates to a sorted list
    all_dates = sorted(all_dates)
    print("All unique dates:", all_dates)  # Optional: Print the dates for verification

else:
    print(f"The folder '{folder_path}' does not exist.")