from datetime import date, timedelta
from io import BytesIO
import base64
import os

import folium
import numpy as np
import rasterio
from matplotlib import cm, pyplot as plt
from rasterio.warp import transform_bounds
from shiny import App, ui, render

mosquito_variables = {
    "Egg Count": "mosquito_Egg_count_",
    "Entomological Inoculation Rate": "mosquito_EIR_",
    "Female Adult Mosquito Count": "mosquito_Female_Adults_count_",
}
climatic_variables = {
    "Rainfal": "mosquito_Rainfall_",
    "Temperature": "mosquito_Temperature_",
}
variable_options = {**mosquito_variables, **climatic_variables}

date_min = date(2021, 1, 1)
date_max = date(2021, 3, 31)

app_ui = ui.page_navbar(
    ui.head_content(
        ui.tags.style(
            """
            .app-shell {
                position: relative;
                display: flex;
                min-height: calc(100vh - var(--bs-navbar-height, 56px));
            }
            .app-sidebar {
                position: absolute;
                top: 1rem;
                left: 1rem;
                width: 320px;
                max-width: 35vw;
                padding: 1rem;
                overflow-y: auto;
                background-color: rgba(248, 249, 250, 0.5);
                border: 1px solid #dee2e6;
                border-radius: 0.5rem;
                box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
                backdrop-filter: blur(6px);
                z-index: 1000;
            }
            .app-main {
                position: relative;
                flex: 1 1 auto;
                padding: 1.5rem;
                margin-left: 0;
                overflow: hidden;
                display: flex;
                flex-direction: column;
                z-index: 0;
            }
            .app-main::after {
                content: "";
                position: absolute;
                inset: 0;
                background: rgba(255, 255, 255, 0.45);
                backdrop-filter: blur(4px);
                pointer-events: none;
                z-index: -1;
            }
            .map-container {
                flex: 1 1 auto;
                min-height: 500px;
                filter: saturate(0.8);
            }
            @media (max-width: 992px) {
                .app-shell {
                    flex-direction: column;
                }
                .app-sidebar {
                    position: static;
                    width: 100%;
                    max-width: none;
                    margin: 0 0 1rem 0;
                }
                .app-main {
                    margin-left: 0;
                }
            }
            """
        )
    ),
    ui.nav_panel(
        "Dashboard",
        ui.div(
            {"class": "app-shell"},
            ui.div(
                {"class": "app-sidebar"},
                ui.h3("Variables"),
                ui.input_radio_buttons(
                    "selected_variable",
                    "Select variable:",
                    choices=list(variable_options.keys()),
                    selected=list(variable_options.keys())[0],
                ),
                ui.input_slider(
                    "selected_date",
                    "Select date:",
                    min=date_min,
                    max=date_max,
                    value=date_min,
                    step=timedelta(days=1),
                ),
            ),
            ui.div(
                {"class": "app-main"},
                ui.div(
                    {"class": "map-container"},
                    ui.output_ui("leaflet_map"),
                ),
            ),
        ),
    ),
    title="Raster Viewer",
)

def server(input, output, session):
    @output
    @render.ui
    def leaflet_map():
        m = folium.Map(
            location=[-1.286389, 36.817223],
            zoom_start=5,
            tiles="CartoDB positron",
            width="100%",
            height="100%",
        )
        choice = input.selected_variable()
        selected_date = input.selected_date()
        if choice and selected_date:
            prefix = variable_options.get(choice, "")
            date_str = selected_date.strftime("%Y%m%d")
            tiff_name = f"{prefix}{date_str}.tif"
            tiff_path = os.path.join("rasters_by_date", tiff_name)
            if os.path.exists(tiff_path):
                with rasterio.open(tiff_path) as src:
                    band = src.read(1, masked=True).astype(float)
                    bounds = src.bounds
                    crs = src.crs

                if crs is not None and crs.to_string() != "EPSG:4326":
                    bounds = transform_bounds(crs, "EPSG:4326", *bounds)

                masked_band = np.ma.masked_invalid(band)
                if masked_band.count() > 0:
                    data = masked_band.filled(np.nan)
                    vmin = np.nanmin(data)
                    vmax = np.nanmax(data)
                    norm = np.zeros_like(data)
                    if not np.isclose(vmin, vmax):
                        norm = (data - vmin) / (vmax - vmin)
                    norm = np.ma.array(norm, mask=~np.isfinite(data))
                    cmap = cm.get_cmap("viridis").copy()
                    cmap.set_bad(alpha=0)
                    buf = BytesIO()
                    plt.imsave(buf, norm, cmap=cmap, format="png")
                    buf.seek(0)
                    img_b64 = base64.b64encode(buf.read()).decode("utf-8")
                    image_uri = f"data:image/png;base64,{img_b64}"
                    folium.raster_layers.ImageOverlay(
                        image=image_uri,
                        bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
                        opacity=0.7,
                    ).add_to(m)
        folium.LayerControl().add_to(m)
        return ui.HTML(m._repr_html_())

app = App(app_ui, server)


