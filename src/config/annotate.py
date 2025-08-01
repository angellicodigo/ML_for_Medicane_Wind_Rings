import argparse
from tqdm import tqdm
import pandas as pd
import os
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from matplotlib.colors import BoundaryNorm
from matplotlib.axes import Axes
import cartopy.crs as ccrs
import numpy as np

PATH_INFO = r'data\processed\annotations_SS.txt'
PATH_DATASET = r'data\processed\dataset'

MEDICANES = [1328, 1461, 1542, 1575, 1622, 1702]
OVER_LAND = [848, 849, 860, 864, 865, 868, 871, 873, 889, 900, 907, 926, 940, 943, 950, 951, 969, 981, 985, 988, 992, 1001, 1018, 1023, 1025, 1030, 1033, 1034, 1041, 1043, 1060, 1064, 1072, 1089, 1094, 1107, 1112, 1126, 1147, 1154, 1166, 1180, 1185, 1199, 1206, 1214, 1215, 1223, 1225, 1232, 1257, 1262, 1264, 1273,
             1274, 1276, 1306, 1308, 1317, 1318, 1322, 1327, 1341, 1365, 1392, 1404, 1405, 1408, 1414, 1420, 1441, 1450, 1452, 1453, 1456, 1484, 1491, 1492, 1496, 1497, 1533, 1535, 1562, 1563, 1568, 1569, 1570, 1583, 1595, 1596, 1603, 1605, 1608, 1612, 1614, 1615, 1616, 1625, 1648, 1649, 1650, 1651, 1664, 1666, 1686, 1700]
EXCLUDE = [1542, 1622, 1466, 1500, 1674]


def annotate(window_size: float) -> None:
    df = pd.read_csv(PATH_INFO, sep=r'\t', engine='python')
    datasets_list = []
    results_list = []
    history_list = []
    remove_list = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Loading datasets into memory"):
        cyclone_id = row['cyclone_id']
        if cyclone_id in MEDICANES:
            results_list.append(row['label'])
        elif (cyclone_id not in OVER_LAND) and (cyclone_id not in EXCLUDE):
            if (row['lon'] != -np.nan) and (row['lat'] != -np.nan):
                if (row['label'] == 'idk') or (int(row['slabel']) != int(row['label'])):
                    file_path = os.path.join(PATH_DATASET, row['file_name'])
                    ds = xr.open_dataset(file_path)
                    datasets_list.append((row, ds))
                    ds.close()

    index = [0]  # A list with 0 because list is global but integer is not
    cbar_prev = [None]

    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_axes([0.05, 0.15, 0.9, 0.8],  # type: ignore
                      projection=ccrs.PlateCarree())

    area1 = plt.axes([0.1, 0.02, 0.15, 0.07])  # type: ignore
    area2 = plt.axes([0.3, 0.02, 0.15, 0.07])  # type: ignore
    area3 = plt.axes([0.5, 0.02, 0.15, 0.07])  # type: ignore
    area4 = plt.axes([0.7, 0.02, 0.15, 0.07])  # type: ignore

    button_true = Button(area1, 'Is a Closed Ring',
                         color='green', hovercolor='lightgreen')
    button_false = Button(area2, 'Not a Closed Ring',
                          color='red', hovercolor='lightcoral')
    button_remove = Button(area3, 'Do not include',
                           color='gray', hovercolor='lightgray')
    button_back = Button(area4, 'Back', color='blue', hovercolor='lightblue')

    def update_plot():
        ax.clear()
        boundaries = np.arange(0, 32.6, 2.5)
        cmap = plt.get_cmap("turbo")
        norm = BoundaryNorm(boundaries, ncolors=cmap.N)
        row, ds = datasets_list[index[0]]
        U = ds['wind_speed'] * np.sin(np.radians(ds['wind_dir']))
        V = ds['wind_speed'] * np.cos(np.radians(ds['wind_dir']))
        quiver = ax.quiver(ds['lon'], ds['lat'], U, V, ds['wind_speed'],
                           cmap=cmap, transform=ccrs.PlateCarree(), scale=500, pivot='mid', norm=norm)
        if cbar_prev[0] is not None:
            cbar_prev[0].update_normal(quiver)
        else:
            cbar_prev[0] = fig.colorbar(quiver, ax=ax)  # type: ignore
        cbar_prev[0].set_label("Wind Speed (m/s)")
        cbar_prev[0].set_ticks(boundaries)  # type: ignore
        ax.coastlines()  # type: ignore
        gridlines = ax.gridlines(draw_labels=True)  # type: ignore
        gridlines.top_labels = False
        gridlines.right_labels = False
        gridlines.bottom_labels = True
        gridlines.left_labels = True
        ax.set_xlim(round(row['lon']-window_size),
                    round(row['lon']+window_size))
        ax.set_ylim(round(row['lat']-window_size),
                    round(row['lat']+window_size))
        ax.plot(row['lon'], row['lat'], 'x', markersize=10,
                color="black", transform=ccrs.PlateCarree())
        plot_top_five(ax, ds)
        fig.suptitle(f"{row['file_name']}")
        fig.canvas.draw()

    def isTrue(event):
        results_list.append(1)
        history_list.append("label")
        next()

    def isFalse(event):
        results_list.append(0)
        history_list.append("label")
        next()

    def remove(event):
        file_name = datasets_list[index[0]][0]['file_name']
        remove_list.append(file_name)
        next()

    def back(event):
        if index[0] == 0:
            return
        if len(history_list) == 0:
            return
        index[0] -= 1
        action = history_list.pop()
        if action == "label":
            results_list.pop()
        elif action == "exclude":
            remove_list.pop()
        update_plot()

    def next():
        index[0] += 1
        if index[0] < len(datasets_list):
            update_plot()
        else:
            df['label'] = results_list
            save_path = os.path.join(
                PATH_DATASET, f'new_{os.path.basename(PATH_INFO)}')
            df.to_csv(save_path, index=False)
            plt.close()

    button_true.on_clicked(isTrue)
    button_false.on_clicked(isFalse)
    button_remove.on_clicked(remove)
    button_back.on_clicked(back)
    update_plot()
    plt.show()


def plot_top_five(ax: Axes, ds: xr.Dataset) -> None:
    wind_speed = ds['wind_speed'].values.flatten()
    wind_speed = np.nan_to_num(wind_speed, nan=-np.inf)
    lon = ds['lon'].values.flatten()
    lat = ds['lat'].values.flatten()
    points = np.argsort(wind_speed)[::-1]
    indices = points[:5]
    lon = lon[indices]
    lat = lat[indices]
    ax.scatter(lon, lat, s=100, marker='x', color="purple",
               transform=ccrs.PlateCarree())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--window_size", type=float, default=3)
    args = parser.parse_args()
    annotate(args.window_size)
